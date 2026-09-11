"""Capture a complete trainer reference sequence for MotionGuard Unity.

This tool stores ordered, normalized joint-angle features rather than an averaged pose.
Copy its output into MotionGuardUnity/Assets/StreamingAssets/MotionGuard/references/
and explicitly mark that file and its catalogue entry as approved only after trainer review.

Player scan
-----------
Before recording starts, the script runs a scan phase (controlled by
--scan-seconds) that locks onto the person standing in frame.  Every
subsequent frame is filtered through PlayerLock.accepts() so bystanders
walking behind the player cannot contaminate the reference sequence.

The lock is scale-invariant: the tolerance window is expressed as a multiple
of the player's shoulder width, so it works identically for players of any
height or at any distance from the camera.

Controls during scan
--------------------
  Q / Esc  Cancel and quit
  R        Reset and restart the scan
"""
import argparse
import json
import math
import sys
import time

import cv2
import mediapipe as mp
from player_lock import scan_for_player

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def angle(a, b, c):
    u = (a.x - b.x, a.y - b.y)
    v = (c.x - b.x, c.y - b.y)
    magnitude = math.hypot(*u) * math.hypot(*v)
    if magnitude < 1e-6:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, (u[0] * v[0] + u[1] * v[1]) / magnitude)))) / 180.0


def features(landmarks, pose):
    p = pose.PoseLandmark
    left_shoulder, right_shoulder = landmarks[p.LEFT_SHOULDER], landmarks[p.RIGHT_SHOULDER]
    left_hip, right_hip = landmarks[p.LEFT_HIP], landmarks[p.RIGHT_HIP]
    left_knee, right_knee = landmarks[p.LEFT_KNEE], landmarks[p.RIGHT_KNEE]
    left_ankle, right_ankle = landmarks[p.LEFT_ANKLE], landmarks[p.RIGHT_ANKLE]
    left_foot, right_foot = landmarks[p.LEFT_FOOT_INDEX], landmarks[p.RIGHT_FOOT_INDEX]
    center_shoulder = type("Point", (), {
        "x": (left_shoulder.x + right_shoulder.x) / 2,
        "y": (left_shoulder.y + right_shoulder.y) / 2,
    })()
    center_hip = type("Point", (), {
        "x": (left_hip.x + right_hip.x) / 2,
        "y": (left_hip.y + right_hip.y) / 2,
    })()
    up = type("Point", (), {"x": center_shoulder.x, "y": center_shoulder.y - 1})()
    return [
        angle(landmarks[p.LEFT_ELBOW], left_shoulder, left_hip),
        angle(landmarks[p.RIGHT_ELBOW], right_shoulder, right_hip),
        angle(left_shoulder, landmarks[p.LEFT_ELBOW], landmarks[p.LEFT_WRIST]),
        angle(right_shoulder, landmarks[p.RIGHT_ELBOW], landmarks[p.RIGHT_WRIST]),
        angle(left_shoulder, left_hip, left_knee),
        angle(right_shoulder, right_hip, right_knee),
        angle(left_hip, left_knee, left_ankle),
        angle(right_hip, right_knee, right_ankle),
        angle(left_knee, left_ankle, left_foot),
        angle(right_knee, right_ankle, right_foot),
        angle(center_hip, center_shoulder, up),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Record a MotionGuard trainer reference sequence with player lock."
    )
    parser.add_argument("technique_id", help="Technique identifier (e.g. punch)")
    parser.add_argument("output", help="Output JSON file path")
    parser.add_argument(
        "--seconds", type=float, default=3.0,
        help="Recording duration in seconds (default: 3)"
    )
    parser.add_argument(
        "--scan-seconds", type=float, default=5.0,
        help="Player scan window in seconds before recording starts (default: 5)"
    )
    args = parser.parse_args()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise SystemExit("Cannot open camera.")

    pose_api = mp.solutions.pose
    required_indices = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]

    with pose_api.Pose(
        model_complexity=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    ) as detector:
        # ── SCAN PHASE ──────────────────────────────────────────────────
        # Lock onto the player before recording so bystanders are ignored.
        try:
            lock = scan_for_player(
                cap, detector, pose_api,
                scan_seconds=args.scan_seconds,
                window_name="MotionGuard — Player Scan",
            )
        except RuntimeError as exc:
            cap.release()
            cv2.destroyAllWindows()
            raise SystemExit(str(exc))

        # ── RECORDING PHASE ─────────────────────────────────────────────
        frames = []
        bystander_frames_skipped = 0
        start = time.time()

        while time.time() - start < args.seconds:
            ok, frame = cap.read()
            if not ok:
                continue

            result = detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            landmarks = result.pose_landmarks.landmark if result.pose_landmarks else None

            if landmarks:
                if not lock.accepts(landmarks):
                    # Bystander or tracker drift — skip this frame
                    bystander_frames_skipped += 1
                    cv2.putText(
                        frame,
                        "BYSTANDER / TRACKER DRIFT — frame skipped",
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 60, 255), 2, cv2.LINE_AA,
                    )
                else:
                    # Accepted as the locked player — check full visibility
                    if all(landmarks[i].visibility >= 0.55 for i in required_indices):
                        frames.append({"values": features(landmarks, pose_api)})

            lock.draw_overlay(frame, landmarks)
            remaining = max(0.0, args.seconds - (time.time() - start))
            cv2.putText(
                frame,
                f"Recording {args.technique_id}: {len(frames)} frames  |  {remaining:.1f}s left",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 255, 0), 2, cv2.LINE_AA,
            )
            cv2.imshow("MotionGuard Unity reference recorder", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()

    print(f"Recorded {len(frames)} valid frames  "
          f"({bystander_frames_skipped} bystander/drift frames skipped).")

    if len(frames) < 18:
        raise SystemExit(
            f"Only {len(frames)} valid frames recorded; at least 18 are required. "
            "Ensure your full body stays in frame during recording."
        )

    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "techniqueId": args.technique_id,
                "featureVersion": 2,
                "trainerApproved": False,
                "frames": frames,
            },
            fh,
            indent=2,
        )
    print(f"Saved {len(frames)} frames to {args.output}.")
    print("Set trainerApproved and readyForEvaluation only after trainer review.")


if __name__ == "__main__":
    main()
