using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using Mediapipe;
using Mediapipe.Tasks.Core;
using Mediapipe.Tasks.Vision.PoseLandmarker;
using Mediapipe.Unity.Experimental;
using UnityEngine;
using MotionGuard;

namespace MotionGuard.MediaPipeAdapter {
    public sealed class MediaPipePoseLandmarkerAdapter : MonoBehaviour {
        [SerializeField] MediaPipePoseBridge poseBridge;
        [SerializeField] WebcamPreview webcamPreview;
        [SerializeField, Range(.1f, 1f)] float minDetectionConfidence = .5f;
        [SerializeField, Range(.1f, 1f)] float minTrackingConfidence = .5f;

        const string ModelFileName = "pose_landmarker_full.bytes";
        PoseLandmarker landmarker;
        TextureFrame inputFrame;
        PoseLandmarkerResult result;
        long lastTimestamp;

        // Invoked by the package-independent bootstrap through SendMessage.
        public void Configure(object[] configuration) {
            if (configuration == null || configuration.Length != 2) return;
            poseBridge = configuration[0] as MediaPipePoseBridge;
            webcamPreview = configuration[1] as WebcamPreview;
        }

        IEnumerator Start() {
            while (webcamPreview == null || !webcamPreview.IsReady || webcamPreview.CameraTexture == null) yield return null;

            var modelPath = Path.Combine(Application.streamingAssetsPath, "MediaPipe", ModelFileName);
            if (!File.Exists(modelPath)) {
                Debug.LogError($"MotionGuard MediaPipe model is missing: {modelPath}");
                yield break;
            }

            var options = new PoseLandmarkerOptions(
                new BaseOptions(BaseOptions.Delegate.CPU, modelAssetBuffer: File.ReadAllBytes(modelPath)),
                runningMode: Mediapipe.Tasks.Vision.Core.RunningMode.VIDEO,
                numPoses: 1,
                minPoseDetectionConfidence: minDetectionConfidence,
                minPosePresenceConfidence: minDetectionConfidence,
                minTrackingConfidence: minTrackingConfidence);
            landmarker = PoseLandmarker.CreateFromOptions(options);
            result = PoseLandmarkerResult.Alloc(options.numPoses);
            StartCoroutine(ProcessCamera());
        }

        IEnumerator ProcessCamera() {
            while (enabled && landmarker != null) {
                var camera = webcamPreview != null ? webcamPreview.CameraTexture : null;
                if (camera == null || !camera.isPlaying || !camera.didUpdateThisFrame || camera.width <= 16) {
                    yield return null;
                    continue;
                }

                if (inputFrame == null || inputFrame.width != camera.width || inputFrame.height != camera.height) {
                    inputFrame?.Dispose();
                    inputFrame = new TextureFrame(camera.width, camera.height, TextureFormat.RGBA32);
                }

                // Orient input pixels exactly like the preview. This is required by the
                // MediaPipe Unity plugin for WebCamTexture landmark coordinates to align.
                webcamPreview.GetMediaPipeFlip(out var flipHorizontally, out var flipVertically);
                inputFrame.ReadTextureOnCPU(camera, flipHorizontally, flipVertically);
                using (var image = inputFrame.BuildCPUImage()) {
                    var timestamp = Math.Max(++lastTimestamp, (long)(Time.realtimeSinceStartup * 1000));
                    if (landmarker.TryDetectForVideo(image, timestamp, null, ref result)) SubmitPoseResult(result);
                    else poseBridge?.Clear();
                }
                yield return null;
            }
        }

        public void SubmitPoseResult(PoseLandmarkerResult result) {
            if (poseBridge == null) return;
            if (result.poseLandmarks == null || result.poseLandmarks.Count == 0 || result.poseLandmarks[0].landmarks == null) {
                poseBridge.Clear();
                return;
            }

            var source = result.poseLandmarks[0].landmarks;
            var landmarks = new List<PoseLandmark>(source.Count);
            foreach (var landmark in source) {
                landmarks.Add(new PoseLandmark {
                    x = landmark.x,
                    y = landmark.y,
                    z = landmark.z,
                    visibility = landmark.visibility ?? landmark.presence ?? 0f
                });
            }
            var detection = DetectTechnique(landmarks);
            poseBridge.SubmitLandmarks(landmarks, detection.technique, detection.confidence);
        }

        static (string technique, float confidence) DetectTechnique(IReadOnlyList<PoseLandmark> landmarks) {
            const int LeftShoulder = 11, RightShoulder = 12, LeftElbow = 13, RightElbow = 14, LeftWrist = 15, RightWrist = 16;
            if (landmarks == null || landmarks.Count <= RightWrist) return ("unknown", 0f);

            var leftShoulder = landmarks[LeftShoulder]; var rightShoulder = landmarks[RightShoulder];
            var leftElbow = landmarks[LeftElbow]; var rightElbow = landmarks[RightElbow];
            var leftWrist = landmarks[LeftWrist]; var rightWrist = landmarks[RightWrist];
            if (leftShoulder == null || rightShoulder == null || leftElbow == null || rightElbow == null || leftWrist == null || rightWrist == null) return ("unknown", 0f);

            var shoulderWidth = Vector2.Distance(Point(leftShoulder), Point(rightShoulder));
            if (shoulderWidth < .06f) return ("unknown", 0f);

            // "Outward" is measured relative to the shoulder line, not screen left/right.
            // This is invariant when a webcam preview is mirrored.
            var leftPunch = IsOutwardExtended(leftShoulder, rightShoulder, leftElbow, leftWrist, shoulderWidth);
            var rightPunch = IsOutwardExtended(rightShoulder, leftShoulder, rightElbow, rightWrist, shoulderWidth);
            var leftGuard = IsGuarding(leftShoulder, leftWrist, shoulderWidth);
            var rightGuard = IsGuarding(rightShoulder, rightWrist, shoulderWidth);
            if ((leftPunch && rightGuard) || (rightPunch && leftGuard)) return ("punch", .85f);

            var leftRaised = leftWrist.y < leftShoulder.y - shoulderWidth * .15f;
            var rightRaised = rightWrist.y < rightShoulder.y - shoulderWidth * .15f;
            var handsApart = Vector2.Distance(Point(leftWrist), Point(rightWrist)) > shoulderWidth * .65f;
            if (leftRaised && rightRaised && handsApart) return ("block", .80f);

            // A step-back exit is temporal; only the DTW sequence evaluator can classify it
            // reliably. Do not guess from a participant's absolute screen position.
            return ("unknown", .30f);
        }

        static bool IsOutwardExtended(PoseLandmark shoulder, PoseLandmark oppositeShoulder, PoseLandmark elbow, PoseLandmark wrist, float shoulderWidth) {
            var shoulderToWrist = Point(wrist) - Point(shoulder);
            var outwardAxis = (Point(shoulder) - Point(oppositeShoulder)).normalized;
            var straightness = Vector2.Angle(Point(shoulder) - Point(elbow), Point(wrist) - Point(elbow)) / 180f;
            return Vector2.Dot(shoulderToWrist, outwardAxis) > shoulderWidth * .45f &&
                   shoulderToWrist.magnitude > shoulderWidth * .65f && straightness > .75f;
        }

        static bool IsGuarding(PoseLandmark shoulder, PoseLandmark wrist, float shoulderWidth) {
            var offset = Point(wrist) - Point(shoulder);
            return offset.magnitude < shoulderWidth * 1.05f && wrist.y < shoulder.y + shoulderWidth * .35f;
        }

        static Vector2 Point(PoseLandmark landmark) => new Vector2(landmark.x, landmark.y);

        void OnDestroy() {
            inputFrame?.Dispose();
            landmarker?.Close();
        }
    }
}
