using System.Collections.Generic;
using UnityEngine;

namespace MotionGuard {
    // Package-independent receiver: call SubmitLandmarks from the selected MediaPipe Unity package's callback.
    public class MediaPipePoseBridge : MonoBehaviour {
        public PoseFrame LatestFrame { get; private set; }
        public bool HasFreshFrame => LatestFrame != null && Time.unscaledTime-LatestFrame.timestamp < .25f;
        public void SubmitLandmarks(List<PoseLandmark> landmarks, string detectedTechnique = "Unknown", float detectionConfidence = 0f) {
            LatestFrame = new PoseFrame {
                timestamp = Time.unscaledTime,
                landmarks = landmarks,
                detectedTechnique = detectedTechnique,
                detectionConfidence = detectionConfidence
            };
        }
        public void Clear() { LatestFrame=null; }
    }
}
