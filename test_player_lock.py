"""Unit tests for player_lock.py: verifying scale-invariance and bystander rejection."""

import unittest
from types import SimpleNamespace
from player_lock import PlayerLock, _L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP, _BODY_INDICES


def create_landmark(x, y, z=0.0, visibility=0.9):
    return SimpleNamespace(x=x, y=y, z=z, visibility=visibility)


def create_body_landmarks(cx, cy, shoulder_width=0.20, hip_width=0.16, torso_height=0.30):
    """Generate a mock list of 33 landmarks for a player at (cx, cy)."""
    lms = [create_landmark(cx, cy, 0.0, 0.9) for _ in range(33)]

    half_sw = shoulder_width / 2.0
    half_hw = hip_width / 2.0
    half_th = torso_height / 2.0

    lms[_L_SHOULDER] = create_landmark(cx - half_sw, cy - half_th, 0.0, 0.95)
    lms[_R_SHOULDER] = create_landmark(cx + half_sw, cy - half_th, 0.0, 0.95)
    lms[_L_HIP] = create_landmark(cx - half_hw, cy + half_th, 0.0, 0.95)
    lms[_R_HIP] = create_landmark(cx + half_hw, cy + half_th, 0.0, 0.95)

    return lms


class TestPlayerLock(unittest.TestCase):
    def test_scan_and_lock_lifecycle(self):
        lock = PlayerLock(stable_frames=5)
        self.assertFalse(lock.is_locked)
        self.assertEqual(lock.scan_progress, 0.0)

        # Feed 4 frames
        for _ in range(4):
            lms = create_body_landmarks(0.5, 0.5, shoulder_width=0.20)
            res = lock.scan(lms)
            self.assertFalse(res)
            self.assertFalse(lock.is_locked)

        # 5th frame locks
        lms = create_body_landmarks(0.5, 0.5, shoulder_width=0.20)
        res = lock.scan(lms)
        self.assertTrue(res)
        self.assertTrue(lock.is_locked)
        self.assertEqual(lock.scan_progress, 1.0)

    def test_scale_invariance_small_player(self):
        """A small player (e.g. child or far away) with narrow shoulder_width=0.10."""
        lock = PlayerLock(stable_frames=3, tolerance_factor=1.8)
        for _ in range(3):
            lock.scan(create_body_landmarks(0.5, 0.5, shoulder_width=0.10))
        self.assertTrue(lock.is_locked)

        # Small movement within tolerance is accepted
        small_move = create_body_landmarks(0.55, 0.52, shoulder_width=0.10)
        self.assertTrue(lock.accepts(small_move))

        # Bystander walking to the side (dx=0.25 -> 2.5 shoulder widths away) is rejected
        bystander_side = create_body_landmarks(0.75, 0.5, shoulder_width=0.10)
        self.assertFalse(lock.accepts(bystander_side))

        # Bystander walking directly behind (cx=0.5, cy=0.5) but smaller scale (0.04 vs 0.10) is rejected
        bystander_behind = create_body_landmarks(0.5, 0.5, shoulder_width=0.04)
        self.assertFalse(lock.accepts(bystander_behind))

    def test_scale_invariance_large_player(self):
        """A large player (tall adult close to camera) with shoulder_width=0.30."""
        lock = PlayerLock(stable_frames=3, tolerance_factor=1.8)
        for _ in range(3):
            lock.scan(create_body_landmarks(0.5, 0.5, shoulder_width=0.30))
        self.assertTrue(lock.is_locked)

        # Large player takes a step or punch: movement of 0.20 is within 1.8 * 0.30 = 0.54
        player_punch = create_body_landmarks(0.60, 0.52, shoulder_width=0.28)
        self.assertTrue(lock.accepts(player_punch))

        # Bystander passing behind (cx=0.52, cy=0.5) but with background scale (0.12 vs 0.30) is rejected
        bystander_behind = create_body_landmarks(0.52, 0.5, shoulder_width=0.12)
        self.assertFalse(lock.accepts(bystander_behind))

    def test_reset(self):
        lock = PlayerLock(stable_frames=2)
        for _ in range(2):
            lock.scan(create_body_landmarks(0.5, 0.5, shoulder_width=0.20))
        self.assertTrue(lock.is_locked)

        lock.reset()
        self.assertFalse(lock.is_locked)
        self.assertEqual(lock.scan_progress, 0.0)


if __name__ == "__main__":
    unittest.main()
