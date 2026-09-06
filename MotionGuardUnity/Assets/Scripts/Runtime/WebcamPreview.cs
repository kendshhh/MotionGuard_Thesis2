using System.Collections;
using UnityEngine;
using UnityEngine.UI;

namespace MotionGuard {
    public class WebcamPreview : MonoBehaviour {
        [SerializeField] RawImage target;
        [SerializeField] bool mirrorPreview = true;
        [SerializeField] bool invertMediaPipeVertical = true;
        WebCamTexture cameraTexture;
        public WebCamTexture CameraTexture => cameraTexture;
        public bool MirrorPreview => mirrorPreview;
        public bool IsReady { get; private set; }
        public string Status { get; private set; } = "Starting camera...";

        public void Configure(RawImage previewTarget) {
            target = previewTarget;
            if (cameraTexture != null && target) target.texture = cameraTexture;
            if (isActiveAndEnabled) StartCoroutine(StartCamera());
        }

        void OnEnable() {
            if (target) StartCoroutine(StartCamera());
        }

        IEnumerator StartCamera() {
            if (cameraTexture != null && cameraTexture.isPlaying) yield break;
            IsReady = false;
            Status = "Requesting camera access...";
            if (!Application.HasUserAuthorization(UserAuthorization.WebCam)) {
                yield return Application.RequestUserAuthorization(UserAuthorization.WebCam);
            }
            if (!Application.HasUserAuthorization(UserAuthorization.WebCam)) {
                Status = "Camera permission was denied.";
                yield break;
            }
            var devices = WebCamTexture.devices;
            if (devices == null || devices.Length == 0) {
                Status = "No camera detected. Connect a webcam and press Play again.";
                yield break;
            }
            cameraTexture = new WebCamTexture(devices[0].name, 1280, 720, 30);
            cameraTexture.Play();
            if (target) target.texture = cameraTexture;
            var timeout = Time.realtimeSinceStartup + 3f;
            while (cameraTexture.width <= 16 && Time.realtimeSinceStartup < timeout) yield return null;
            IsReady = cameraTexture.width > 16;
            ApplyDisplayOrientation();
            Status = IsReady ? "Camera ready" : "Camera is not returning frames.";
        }

        void Update() {
            if (IsReady && target && cameraTexture != null) ApplyDisplayOrientation();
        }

        void ApplyDisplayOrientation() {
            if (target == null || cameraTexture == null) return;

            // MediaPipe sees the original camera pixels. The preview and landmark overlay are
            // children of this RawImage, so rotating the parent keeps all three in sync.
            target.rectTransform.localEulerAngles = new Vector3(0f, 0f, -cameraTexture.videoRotationAngle);
            var verticalSign = cameraTexture.videoVerticallyMirrored ? -1f : 1f;
            var verticalOrigin = cameraTexture.videoVerticallyMirrored ? 1f : 0f;
            var horizontalSign = mirrorPreview ? -1f : 1f;
            var horizontalOrigin = mirrorPreview ? 1f : 0f;
            target.uvRect = new Rect(horizontalOrigin, verticalOrigin, horizontalSign, verticalSign);
        }

        // The Windows WebCamTexture readback path used by this project has the opposite
        // vertical convention to the preview texture. Keep this compensation explicit so
        // MediaPipe landmarks move in the same direction as the on-screen person.
        public void GetMediaPipeFlip(out bool flipHorizontally, out bool flipVertically) {
            var rotation = cameraTexture != null ? cameraTexture.videoRotationAngle : 0;
            var isInverted = rotation == 90 || rotation == 270;
            flipHorizontally = !isInverted && mirrorPreview;
            flipVertically = !mirrorPreview
                ? !(cameraTexture != null && cameraTexture.videoVerticallyMirrored)
                : isInverted
                    ? cameraTexture != null && cameraTexture.videoVerticallyMirrored
                    : !(cameraTexture != null && cameraTexture.videoVerticallyMirrored);
            if (invertMediaPipeVertical) flipVertically = !flipVertically;
        }

        void OnDisable(){if(cameraTexture!=null&&cameraTexture.isPlaying)cameraTexture.Stop();}
    }
}
