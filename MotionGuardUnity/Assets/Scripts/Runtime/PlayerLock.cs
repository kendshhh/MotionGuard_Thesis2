using System;
using System.Collections.Generic;
using UnityEngine;

namespace MotionGuard {
    /// <summary>
    /// Scan-then-lock player isolation for MotionGuard.
    /// Scale-invariant: thresholds scale with the player's locked shoulder width,
    /// so the tracking window is equally strict regardless of the player's physical
    /// height, body size, or distance from the camera.
    /// Rejects background bystanders crossing behind the player.
    /// </summary>
    public class PlayerLock {
        const int L_SHOULDER = 11;
        const int R_SHOULDER = 12;
        const int L_HIP = 23;
        const int R_HIP = 24;

        public float MinVisibility { get; set; } = 0.50f;
        public int StableFramesRequired { get; set; } = 15;
        public float ToleranceFactor { get; set; } = 1.8f;
        public float ScanTimeoutSeconds { get; set; } = 8.0f;

        readonly List<Vector2> anchorSamples = new();
        readonly List<float> scaleSamples = new();

        Vector2 lockedAnchor;
        float lockedScale;
        float scanStartTime = -1f;

        public bool IsLocked { get; private set; }
        public bool IsScanning => scanStartTime >= 0f && !IsLocked && !IsTimedOut;
        public bool IsTimedOut => scanStartTime >= 0f && !IsLocked && (Time.unscaledTime - scanStartTime > ScanTimeoutSeconds);
        public float ScanProgress => IsLocked ? 1.0f : Mathf.Clamp01((float)anchorSamples.Count / Mathf.Max(1, StableFramesRequired));
        public Vector2 LockedAnchor => lockedAnchor;
        public float LockedScale => lockedScale;

        public void BeginScan(float timeoutSeconds = 8.0f) {
            Reset();
            ScanTimeoutSeconds = timeoutSeconds;
            scanStartTime = Time.unscaledTime;
        }

        public void Reset() {
            anchorSamples.Clear();
            scaleSamples.Clear();
            lockedAnchor = Vector2.zero;
            lockedScale = 0f;
            IsLocked = false;
            scanStartTime = -1f;
        }

        public bool Scan(IReadOnlyList<PoseLandmark> landmarks) {
            if (IsLocked) return true;
            if (scanStartTime < 0f) scanStartTime = Time.unscaledTime;

            if (!TryComputeTorso(landmarks, out var anchor, out var scale)) {
                return false;
            }

            anchorSamples.Add(anchor);
            scaleSamples.Add(scale);

            if (anchorSamples.Count >= StableFramesRequired) {
                Vector2 sum = Vector2.zero;
                for (int i = 0; i < anchorSamples.Count; i++) sum += anchorSamples[i];
                lockedAnchor = sum / anchorSamples.Count;

                float scaleSum = 0f;
                for (int i = 0; i < scaleSamples.Count; i++) scaleSum += scaleSamples[i];
                lockedScale = scaleSum / scaleSamples.Count;

                IsLocked = true;
                return true;
            }

            return false;
        }

        public bool Accepts(IReadOnlyList<PoseLandmark> landmarks) {
            if (!IsLocked) return false;
            if (!TryComputeTorso(landmarks, out var anchor, out var scale)) {
                return false;
            }

            // 1. Spatial proximity normalized to player's locked scale (shoulder width)
            float threshold = ToleranceFactor * lockedScale;
            float dist = Vector2.Distance(anchor, lockedAnchor);
            if (dist > threshold) return false;

            // 2. Scale ratio check: prevents MediaPipe jumping to people in the background
            if (lockedScale > 1e-4f && scale > 1e-4f) {
                float ratio = scale / lockedScale;
                if (ratio < 0.55f || ratio > 1.60f) return false;
            }

            return true;
        }

        bool TryComputeTorso(IReadOnlyList<PoseLandmark> landmarks, out Vector2 anchor, out float scale) {
            anchor = Vector2.zero;
            scale = 0f;

            if (landmarks == null || landmarks.Count <= R_HIP) return false;

            var ls = landmarks[L_SHOULDER];
            var rs = landmarks[R_SHOULDER];
            var lh = landmarks[L_HIP];
            var rh = landmarks[R_HIP];

            if (ls.visibility < MinVisibility || rs.visibility < MinVisibility ||
                lh.visibility < MinVisibility || rh.visibility < MinVisibility) {
                return false;
            }

            float sw = Vector2.Distance(new Vector2(ls.x, ls.y), new Vector2(rs.x, rs.y));
            if (sw < 0.04f) return false; // Too far or side profile

            anchor = new Vector2(
                (ls.x + rs.x + lh.x + rh.x) * 0.25f,
                (ls.y + rs.y + lh.y + rh.y) * 0.25f
            );
            scale = sw;
            return true;
        }
    }
}
