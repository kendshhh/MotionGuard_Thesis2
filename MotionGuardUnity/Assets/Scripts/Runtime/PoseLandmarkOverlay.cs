using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace MotionGuard {
    // UI-based overlay: children of the camera RawImage always share its exact bounds and clipping.
    public sealed class PoseLandmarkOverlay : MonoBehaviour {
        const float MinimumVisibility = .35f;
        const float LineThickness = 5f;
        const float BodyDotDiameter = 13f;
        const float FaceDotDiameter = 7f;
        static readonly int[,] connections = {
            // Face and head.
            { 0, 1 }, { 1, 2 }, { 2, 3 }, { 3, 7 }, { 0, 4 }, { 4, 5 }, { 5, 6 }, { 6, 8 }, { 9, 10 },
            // Torso and arms, including hands.
            { 11, 12 }, { 11, 13 }, { 13, 15 }, { 15, 17 }, { 15, 19 }, { 15, 21 },
            { 12, 14 }, { 14, 16 }, { 16, 18 }, { 16, 20 }, { 16, 22 },
            { 11, 23 }, { 12, 24 }, { 23, 24 },
            // Legs and feet.
            { 23, 25 }, { 25, 27 }, { 27, 29 }, { 27, 31 },
            { 24, 26 }, { 26, 28 }, { 28, 30 }, { 28, 32 }
        };
        static readonly int[] visibleLandmarks = {
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
            11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
            23, 24, 25, 26, 27, 28, 29, 30, 31, 32
        };

        MediaPipePoseBridge poseBridge;
        RawImage preview;
        RectTransform overlayRoot;
        readonly List<RectTransform> lineRects = new();
        readonly List<RectTransform> dotRects = new();

        public void Configure(MediaPipePoseBridge bridge, RawImage previewTarget) {
            poseBridge = bridge;
            preview = previewTarget;
            BuildOverlay();
        }

        void Update() {
            if (overlayRoot == null) return;
            var frame = poseBridge != null ? poseBridge.LatestFrame : null;
            if (poseBridge == null || !poseBridge.HasFreshFrame || frame == null || frame.landmarks == null) {
                SetVisible(false);
                return;
            }
            Draw(frame);
        }

        void BuildOverlay() {
            if (preview == null || overlayRoot != null) return;
            if (preview.GetComponent<RectMask2D>() == null) preview.gameObject.AddComponent<RectMask2D>();

            var root = new GameObject("Pose Overlay", typeof(RectTransform));
            root.transform.SetParent(preview.transform, false);
            overlayRoot = root.GetComponent<RectTransform>();
            overlayRoot.anchorMin = Vector2.zero;
            overlayRoot.anchorMax = Vector2.one;
            overlayRoot.offsetMin = Vector2.zero;
            overlayRoot.offsetMax = Vector2.zero;
            overlayRoot.SetAsLastSibling();

            for (var i = 0; i < connections.GetLength(0); i++) lineRects.Add(CreateElement("Bone", new Color(.1f, 1f, .7f, 1f)));
            foreach (var _ in visibleLandmarks) dotRects.Add(CreateElement("Joint", new Color(1f, .86f, .05f, 1f)));
            SetVisible(false);
        }

        RectTransform CreateElement(string name, Color color) {
            var element = new GameObject(name, typeof(RectTransform), typeof(Image), typeof(Outline));
            element.transform.SetParent(overlayRoot, false);
            var image = element.GetComponent<Image>();
            image.color = color;
            image.raycastTarget = false;
            var outline = element.GetComponent<Outline>();
            outline.effectColor = new Color(0f, 0f, 0f, .9f);
            outline.effectDistance = new Vector2(1.5f, -1.5f);
            return element.GetComponent<RectTransform>();
        }

        void Draw(PoseFrame frame) {
            overlayRoot.gameObject.SetActive(true);
            for (var i = 0; i < lineRects.Count; i++) {
                var start = Landmark(frame, connections[i, 0]);
                var end = Landmark(frame, connections[i, 1]);
                var visible = IsVisibleInCamera(start) && IsVisibleInCamera(end);
                lineRects[i].gameObject.SetActive(visible);
                if (visible) PositionLine(lineRects[i], ToLocalPoint(start), ToLocalPoint(end), DisplayScale() * LineThickness);
            }
            for (var i = 0; i < dotRects.Count; i++) {
                var landmark = Landmark(frame, visibleLandmarks[i]);
                var visible = IsVisibleInCamera(landmark);
                dotRects[i].gameObject.SetActive(visible);
                if (visible) {
                    var dot = dotRects[i];
                    dot.anchorMin = dot.anchorMax = new Vector2(.5f, .5f);
                    dot.anchoredPosition = ToLocalPoint(landmark);
                    var diameter = (visibleLandmarks[i] <= 10 ? FaceDotDiameter : BodyDotDiameter) * DisplayScale();
                    dot.sizeDelta = new Vector2(diameter, diameter);
                }
            }
        }

        PoseLandmark Landmark(PoseFrame frame, int index) => index < frame.landmarks.Count ? frame.landmarks[index] : null;

        Vector2 ToLocalPoint(PoseLandmark landmark) {
            // PoseLandmarker coordinates are top-left based. Rotation is applied to the
            // RawImage parent, which also rotates this overlay.
            var rect = overlayRoot.rect;
            // This camera's MediaPipe readback reports Y from the bottom of the image while
            // the screen body is upright. Convert it to the overlay's local coordinates.
            return new Vector2((landmark.x - .5f) * rect.width, (landmark.y - .5f) * rect.height);
        }

        float DisplayScale() => Mathf.Clamp(Mathf.Min(overlayRoot.rect.width, overlayRoot.rect.height) / 576f, .75f, 1.6f);

        static void PositionLine(RectTransform line, Vector2 from, Vector2 to, float thickness) {
            var difference = to - from;
            line.anchorMin = line.anchorMax = new Vector2(.5f, .5f);
            line.pivot = new Vector2(.5f, .5f);
            line.anchoredPosition = (from + to) * .5f;
            line.sizeDelta = new Vector2(difference.magnitude, thickness);
            line.localRotation = Quaternion.Euler(0f, 0f, Mathf.Atan2(difference.y, difference.x) * Mathf.Rad2Deg);
        }

        static bool IsVisibleInCamera(PoseLandmark landmark) {
            return landmark != null && landmark.visibility >= MinimumVisibility && landmark.x >= 0f && landmark.x <= 1f && landmark.y >= 0f && landmark.y <= 1f;
        }

        void SetVisible(bool visible) {
            if (overlayRoot != null) overlayRoot.gameObject.SetActive(visible);
        }
    }
}
