using UnityEngine;
using UnityEngine.UI;

namespace MotionGuard {
    public sealed class MotionGuardGameBootstrap : MonoBehaviour {
        static MotionGuardGameBootstrap instance;
        Text statusText;
        WebcamPreview webcamPreview;
        MediaPipePoseBridge poseBridge;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void CreateGameUi() {
            if (FindObjectOfType<MotionGuardGameBootstrap>() != null) return;
            var root = new GameObject("MotionGuard Game");
            DontDestroyOnLoad(root);
            instance = root.AddComponent<MotionGuardGameBootstrap>();
            instance.BuildUi();
        }

        void BuildUi() {
            var canvasObject = new GameObject("Just Dance UI");
            canvasObject.transform.SetParent(transform, false);
            var canvas = canvasObject.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var canvasScaler = canvasObject.AddComponent<CanvasScaler>();
            canvasScaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            canvasScaler.referenceResolution = new Vector2(1920, 1080);
            canvasScaler.referencePixelsPerUnit = 96;
            canvasObject.AddComponent<GraphicRaycaster>();
            poseBridge = gameObject.AddComponent<MediaPipePoseBridge>();

            var preview = CreateRawImage("Camera Preview", canvasObject.transform, Color.white);
            preview.rectTransform.anchorMin = Vector2.one;
            preview.rectTransform.anchorMax = Vector2.one;
            preview.rectTransform.pivot = Vector2.one;
            // Canvas is configured at 96 pixels/inch: 6 x 6 inches, 1 inch below the top edge.
            preview.rectTransform.anchoredPosition = new Vector2(-24, -96);
            preview.rectTransform.sizeDelta = new Vector2(576, 576);
            webcamPreview = canvasObject.AddComponent<WebcamPreview>();
            webcamPreview.Configure(preview);
            // Keep the package-specific adapter in its own assembly so the core runtime remains package-independent.
            var poseLandmarkerType = System.Type.GetType("MotionGuard.MediaPipeAdapter.MediaPipePoseLandmarkerAdapter, MotionGuard.MediaPipeAdapter");
            if (poseLandmarkerType != null) {
                var poseLandmarker = gameObject.AddComponent(poseLandmarkerType);
                poseLandmarker.SendMessage("Configure", new object[] { poseBridge, webcamPreview }, SendMessageOptions.RequireReceiver);
            } else {
                Debug.LogError("MediaPipe pose adapter could not be loaded.");
            }
            var landmarkOverlay = canvasObject.AddComponent<PoseLandmarkOverlay>();
            landmarkOverlay.Configure(poseBridge, preview);

            var tint = CreateImage("Overlay", canvasObject.transform, new Color(0.02f, 0.04f, 0.08f, 0.38f));
            tint.rectTransform.anchorMin = Vector2.zero;
            tint.rectTransform.anchorMax = Vector2.one;
            tint.rectTransform.offsetMin = Vector2.zero;
            tint.rectTransform.offsetMax = Vector2.zero;

            var header = CreateImage("Header", canvasObject.transform, new Color(0.02f, 0.04f, 0.08f, 0.88f));
            header.rectTransform.anchorMin = new Vector2(0, 1);
            header.rectTransform.anchorMax = Vector2.one;
            header.rectTransform.pivot = new Vector2(0.5f, 1);
            header.rectTransform.offsetMin = new Vector2(0, -110);
            header.rectTransform.offsetMax = Vector2.zero;

            CreateText("MotionGuard", header.transform, 34, TextAnchor.MiddleLeft, Color.white, new Vector2(32, 0), new Vector2(0.55f, 1));
            statusText = CreateText("Starting camera...", header.transform, 18, TextAnchor.MiddleRight, new Color(0.72f, 0.9f, 1f), new Vector2(-32, 0), new Vector2(0.95f, 1));

            var instruction = CreateText("STEP INTO FRAME\nFOLLOW THE MOVEMENT", canvasObject.transform, 28, TextAnchor.MiddleCenter, Color.white, Vector2.zero, new Vector2(0.78f, 0.62f));
            instruction.rectTransform.anchorMin = new Vector2(0.1f, 0.36f);
            instruction.rectTransform.anchorMax = new Vector2(0.9f, 0.68f);
            instruction.rectTransform.offsetMin = Vector2.zero;
            instruction.rectTransform.offsetMax = Vector2.zero;
            preview.transform.SetAsLastSibling();
        }

        void Update() {
            if (statusText && webcamPreview) statusText.text = webcamPreview.Status;
        }

        static Image CreateImage(string name, Transform parent, Color color) {
            var imageObject = new GameObject(name);
            imageObject.transform.SetParent(parent, false);
            var image = imageObject.AddComponent<Image>();
            image.color = color;
            return image;
        }

        static RawImage CreateRawImage(string name, Transform parent, Color color) {
            var imageObject = new GameObject(name);
            imageObject.transform.SetParent(parent, false);
            var image = imageObject.AddComponent<RawImage>();
            image.color = color;
            return image;
        }

        static Text CreateText(string content, Transform parent, int size, TextAnchor alignment, Color color, Vector2 position, Vector2 anchor) {
            var textObject = new GameObject(content);
            textObject.transform.SetParent(parent, false);
            var text = textObject.AddComponent<Text>();
            text.text = content;
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            text.fontSize = size;
            text.alignment = alignment;
            text.color = color;
            text.horizontalOverflow = HorizontalWrapMode.Wrap;
            text.verticalOverflow = VerticalWrapMode.Overflow;
            text.rectTransform.anchorMin = anchor;
            text.rectTransform.anchorMax = anchor;
            text.rectTransform.pivot = anchor;
            text.rectTransform.anchoredPosition = position;
            text.rectTransform.sizeDelta = new Vector2(700, 100);
            return text;
        }
    }
}
