"""Capture a complete trainer reference sequence for MotionGuard Unity.

This tool stores ordered, normalized joint-angle features rather than an averaged pose.
Copy its output into MotionGuardUnity/Assets/StreamingAssets/MotionGuard/references/
and explicitly mark that file and its catalogue entry as approved only after trainer review.
"""
import argparse
import json
import math
import time

import cv2
import mediapipe as mp


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
    center_shoulder = type("Point", (), {"x": (left_shoulder.x + right_shoulder.x) / 2, "y": (left_shoulder.y + right_shoulder.y) / 2})()
    center_hip = type("Point", (), {"x": (left_hip.x + right_hip.x) / 2, "y": (left_hip.y + right_hip.y) / 2})()
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
    parser = argparse.ArgumentParser()
    parser.add_argument("technique_id")
    parser.add_argument("output")
    parser.add_argument("--seconds", type=float, default=3.0)
    args = parser.parse_args()
    cap = cv2.VideoCapture(0)
    pose_api = mp.solutions.pose
    frames = []
    with pose_api.Pose(model_complexity=1, min_detection_confidence=.6, min_tracking_confidence=.6) as detector:
        start = time.time()
        while time.time() - start < args.seconds:
            ok, frame = cap.read()
            if not ok:
                continue
            result = detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if result.pose_landmarks:
                landmarks = result.pose_landmarks.landmark
                required = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
                if all(landmarks[index].visibility >= .55 for index in required):
                    frames.append({"values": features(landmarks, pose_api)})
            cv2.putText(frame, f"Recording {args.technique_id}: {len(frames)} valid frames", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 0), 2)
            cv2.imshow("MotionGuard Unity reference recorder", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    cap.release()
    cv2.destroyAllWindows()
    if len(frames) < 18:
        raise SystemExit(f"Only {len(frames)} valid frames recorded; at least 18 are required.")
    with open(args.output, "w", encoding="utf-8") as file:
        json.dump({"techniqueId": args.technique_id, "featureVersion": 2, "trainerApproved": False, "frames": frames}, file, indent=2)
    print(f"Saved {len(frames)} frames. Set trainerApproved and readyForEvaluation only after approval.")


if __name__ == "__main__":
    main()
