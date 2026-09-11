"""
player_lock.py — Scan-first, scale-invariant player isolation for MotionGuard.

All drift thresholds are expressed as multiples of the locked player's
shoulder width, so the lock is equally strict whether the player is a child
(small apparent body) or an adult at close range (large apparent body).

Landmarks indices follow the MediaPipe Pose convention.
"""

from __future__ import annotations

import time
from typing import Optional

import cv2
import numpy as np

# MediaPipe Pose landmark indices used for the torso anchor
_L_SHOULDER = 11
_R_SHOULDER = 12
_L_HIP = 23
_R_HIP = 24

# All body landmarks used when computing a bounding box for the overlay
_BODY_INDICES = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]


class PlayerLock:
    """Scan-then-lock player tracker.

    How scale-invariance works
    --------------------------
    The torso anchor is the mean of LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP,
    and RIGHT_HIP in MediaPipe normalised [0,1] coordinates. The lock tolerance
    is ``tolerance_factor * shoulder_width``, where ``shoulder_width`` is the
    Euclidean distance between the two shoulder landmarks captured at lock time.

    Because both the anchor and the ruler (shoulder width) come from the same
    normalised coordinate system:
    - A player 3 m away  -> small shoulder_width -> small absolute tolerance.
    - A player 1 m away  -> large shoulder_width -> large absolute tolerance.
    In both cases the window is the same *number of shoulder widths*, so a
    bystander who is more than ``tolerance_factor`` shoulder widths from the
    locked anchor is always rejected, regardless of player size or distance.

    Usage
    -----
    lock = PlayerLock()
    while True:
        if result.pose_landmarks:
            lms = result.pose_landmarks.landmark
            if not lock.is_locked:
                lock.scan(lms)
            elif lock.accepts(lms):
                process(lms)
            # else: bystander — silently skip this frame
        lock.draw_overlay(frame, lms)
    """

    def __init__(
        self,
        *,
        min_visibility: float = 0.55,
        stable_frames: int = 20,
        tolerance_factor: float = 1.8,
        scan_timeout_s: float = 10.0,
    ) -> None:
        self.min_visibility = min_visibility
        self.stable_frames = stable_frames
        self.tolerance_factor = tolerance_factor
        self.scan_timeout_s = scan_timeout_s

        self._anchor_samples: list = []
        self._scale_samples: list = []
        self._locked_anchor: Optional[tuple] = None
        self._locked_scale: float = 0.0
        self._scan_start: Optional[float] = None

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    @property
    def is_locked(self) -> bool:
        return self._locked_anchor is not None

    @property
    def is_timed_out(self) -> bool:
        if self._scan_start is None or self.is_locked:
            return False
        return time.time() - self._scan_start > self.scan_timeout_s

    @property
    def scan_progress(self) -> float:
        if self.is_locked:
            return 1.0
        return min(1.0, len(self._anchor_samples) / max(1, self.stable_frames))

    def scan(self, landmarks) -> bool:
        """Feed one frame during the scan phase.  Returns True once locked."""
        if self.is_locked:
            return True
        if self._scan_start is None:
            self._scan_start = time.time()

        anchor, scale = self._torso_anchor(landmarks)
        if anchor is None:
            return False

        self._anchor_samples.append(anchor)
        self._scale_samples.append(scale)

        if len(self._anchor_samples) >= self.stable_frames:
            self._locked_anchor = (
                float(np.mean([a[0] for a in self._anchor_samples])),
                float(np.mean([a[1] for a in self._anchor_samples])),
            )
            self._locked_scale = float(np.mean(self._scale_samples))
            return True
        return False

    def accepts(self, landmarks) -> bool:
        """Return True if landmarks belong to the locked player.

        Scale-invariant dual verification:
        1. Spatial proximity: torso anchor drift must be within
           `tolerance_factor * locked_shoulder_width`.
        2. Scale consistency: current shoulder width must be within
           [1 - max_scale_deviation, 1 + max_scale_deviation] of locked scale.
           This rejects background bystanders who pass directly behind the player
           (similar X/Y) but are farther away (smaller apparent body size).
        """
        if not self.is_locked:
            return False
        anchor, scale = self._torso_anchor(landmarks)
        if anchor is None:
            return False

        # 1. Torso anchor distance relative to locked player size
        threshold = self.tolerance_factor * self._locked_scale
        dist = float(np.hypot(
            anchor[0] - self._locked_anchor[0],
            anchor[1] - self._locked_anchor[1],
        ))
        if dist > threshold:
            return False

        # 2. Scale ratio check (rejects background bystanders walking behind)
        if self._locked_scale > 1e-4 and scale > 1e-4:
            scale_ratio = scale / self._locked_scale
            # Allow body rotation / punch extension up to ±45% scale change
            if scale_ratio < 0.55 or scale_ratio > 1.60:
                return False

        return True

    def reset(self) -> None:
        """Clear the lock so a fresh scan can begin."""
        self._anchor_samples.clear()
        self._scale_samples.clear()
        self._locked_anchor = None
        self._locked_scale = 0.0
        self._scan_start = None

    def draw_overlay(self, frame, landmarks=None) -> None:
        """Draw bounding box and status bar onto a cv2 BGR frame in-place."""
        h, w = frame.shape[:2]

        if landmarks is not None:
            bb = self._bounding_box_px(landmarks, h, w)
            if bb:
                x1, y1, x2, y2 = bb
                if self.is_locked:
                    color = (0, 220, 80)
                    label = "PLAYER LOCKED"
                else:
                    pulse = int(abs(np.sin(time.time() * 4.0)) * 55 + 200)
                    color = (0, pulse, 255)
                    label = f"SCANNING {int(self.scan_progress * 100)}%"
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, max(y1 - 8, 12)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

        if self.is_locked:
            msg = "Player locked — only the registered player will be recorded"
            bar_color = (30, 160, 50)
        elif self.is_timed_out:
            msg = "Scan timed out — press R to retry  Q to quit"
            bar_color = (20, 20, 180)
        else:
            elapsed = int(time.time() - self._scan_start) if self._scan_start else 0
            remaining = max(0, int(self.scan_timeout_s) - elapsed)
            msg = f"Stand in frame — scanning player  {elapsed}s / {remaining}s remaining"
            bar_color = (140, 80, 20)

        cv2.rectangle(frame, (0, h - 36), (w, h), bar_color, -1)
        cv2.putText(frame, msg, (10, h - 11),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _torso_anchor(self, landmarks):
        """Compute normalised torso centre and shoulder-width ruler.

        Returns (anchor_tuple, shoulder_width) or (None, 0.0) on failure.
        """
        for idx in (_L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP):
            lm = landmarks[idx]
            if lm.visibility < self.min_visibility:
                return None, 0.0

        ls = landmarks[_L_SHOULDER]
        rs = landmarks[_R_SHOULDER]
        lh = landmarks[_L_HIP]
        rh = landmarks[_R_HIP]

        # Shoulder width is the scale ruler: same computation regardless of
        # actual body size because MediaPipe coords are normalised to [0, 1].
        shoulder_width = float(np.hypot(rs.x - ls.x, rs.y - ls.y))
        if shoulder_width < 0.04:
            # Player too far away or turned side-on — unreliable ruler
            return None, 0.0

        cx = (ls.x + rs.x + lh.x + rh.x) / 4.0
        cy = (ls.y + rs.y + lh.y + rh.y) / 4.0
        return (float(cx), float(cy)), shoulder_width

    def _bounding_box_px(self, landmarks, frame_h: int, frame_w: int):
        """Return pixel (x1, y1, x2, y2) bounding box or None."""
        xs, ys = [], []
        for idx in _BODY_INDICES:
            lm = landmarks[idx]
            if lm.visibility >= self.min_visibility:
                xs.append(lm.x)
                ys.append(lm.y)
        if not xs:
            return None
        w_span = max(xs) - min(xs)
        h_span = max(ys) - min(ys)
        pad_x = w_span * 0.15
        pad_y = h_span * 0.10
        x1 = int(max(0.0, min(xs) - pad_x) * frame_w)
        y1 = int(max(0.0, min(ys) - pad_y) * frame_h)
        x2 = int(min(1.0, max(xs) + pad_x) * frame_w)
        y2 = int(min(1.0, max(ys) + pad_y) * frame_h)
        return x1, y1, x2, y2


# ------------------------------------------------------------------ #
#  Convenience function for recording scripts
# ------------------------------------------------------------------ #

def scan_for_player(
    cap,
    detector,
    pose_api,
    scan_seconds: float = 5.0,
    window_name: str = "MotionGuard \u2014 Player Scan",
) -> PlayerLock:
    """Run the scan phase with a live preview.  Blocks until locked.

    Press R to reset the scan, Q / Esc to cancel.
    Raises RuntimeError on timeout or cancellation.
    """
    lock = PlayerLock(scan_timeout_s=scan_seconds)
    print(f"\n\U0001f4f7  PLAYER SCAN \u2014 stand in frame ({scan_seconds:.0f} s window)")
    print("   Keep head, shoulders, hips, knees, and feet fully visible.")

    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        result = detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        landmarks = result.pose_landmarks.landmark if result.pose_landmarks else None

        if landmarks and not lock.is_locked:
            lock.scan(landmarks)

        lock.draw_overlay(frame, landmarks)
        cv2.imshow(window_name, frame)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord("q"), 27):
            cv2.destroyWindow(window_name)
            raise RuntimeError("Player scan cancelled by user (Q / Esc).")

        if key == ord("r"):
            lock.reset()
            print("   \U0001f504 Scan reset \u2014 stand in frame again.")

        if lock.is_locked:
            print("   \u2705 Player locked!")
            cv2.waitKey(700)
            cv2.destroyWindow(window_name)
            return lock

        if lock.is_timed_out:
            cv2.destroyWindow(window_name)
            raise RuntimeError(
                f"Player scan timed out after {scan_seconds:.0f} s. "
                "Ensure full body is visible and well lit, then re-run."
            )
