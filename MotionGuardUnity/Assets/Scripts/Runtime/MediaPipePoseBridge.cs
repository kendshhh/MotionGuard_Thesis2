using System.Collections.Generic;
using UnityEngine;

namespace MotionGuard {
    // Package-independent receiver: call SubmitLandmarks from the selected MediaPipe Unity package's callback.
    public class MediaPipePoseBridge : MonoBehaviour {
        public PlayerLock Lock { get; } = new();
        public PoseFrame LatestFrame { get; private set; }
        public bool HasFreshFrame => LatestFrame != null && Time.unscaledTime - LatestFrame.timestamp < .25f;

        public void SubmitLandmarks(List<PoseLandmark> landmarks, string detectedTechnique = "Unknown", float detectionConfidence = 0f) {
            if (landmarks == null) {
                Clear();
                return;
            }

            // If currently scanning player, feed scan frames
            if (Lock.IsScanning) {
                Lock.Scan(landmarks);
            }

            // If player is locked, reject any frames from bystanders
            if (Lock.IsLocked && !Lock.Accepts(landmarks)) {
                Clear();
                return;
            }

            LatestFrame = new PoseFrame {
                timestamp = Time.unscaledTime,
                landmarks = landmarks,
                detectedTechnique = detectedTechnique,
                detectionConfidence = detectionConfidence
            };
        }

        public void Clear() { LatestFrame = null; }
    }
}
