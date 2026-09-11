"""
RECORD REFERENCE TECHNIQUES - ENHANCED VERSION
With quality validation, multiple samples, and scale-invariant player lock
"""

import cv2
import mediapipe as mp
import json
import numpy as np
import os
import time
import math
from datetime import datetime
from collections import deque
from player_lock import scan_for_player, PlayerLock

# ===== CONFIGURATION =====
TECHNIQUES = ["Punch", "Block", "Escape"]
SAMPLES_PER_TECHNIQUE = 10  # More samples = better accuracy
RECORD_DURATION = 3  # Seconds to hold pose
MIN_FRAMES = 18  # Matches the Unity V1 minimum sequence requirement
OUTPUT_DIR = "reference_data"

# ===== QUALITY THRESHOLDS =====
QUALITY_CONFIG = {
    "Punch": {
        "required_angles": ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow"],
        "min_confidence": 0.5
    },
    "Block": {
        "required_angles": ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow"],
        "min_confidence": 0.5
    },
    "Escape": {
        "required_angles": ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "hip"],
        "min_confidence": 0.5
    }
}

# ===== CREATE OUTPUT DIRECTORY =====
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===== INITIALIZE MEDIAPIPE =====
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def extract_angles(landmarks, frame_shape):
    """Extract joint angles with validation"""
    import math
    angles = {}
    h, w, _ = frame_shape
    
    try:
        # Get key landmarks with validation
        ls = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        rs = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        le = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
        re = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        lw = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
        rw = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        lh = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        rh = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        
        # Check visibility
        if ls.visibility < 0.3 or rs.visibility < 0.3:
            return None
        
        # Shoulder angles
        angles["left_shoulder"] = math.degrees(math.atan2(
            abs(lw.x - ls.x), abs(lw.y - ls.y) + 0.001
        ))
        angles["right_shoulder"] = math.degrees(math.atan2(
            abs(rw.x - rs.x), abs(rw.y - rs.y) + 0.001
        ))
        
        # Elbow angles
        def angle_between(p1, p2, p3):
            v1 = (p1.x - p2.x, p1.y - p2.y)
            v2 = (p3.x - p2.x, p3.y - p2.y)
            dot = v1[0]*v2[0] + v1[1]*v2[1]
            mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
            mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
            if mag1 < 0.001 or mag2 < 0.001:
                return None
            cos_angle = max(-1, min(1, dot / (mag1 * mag2)))
            return math.degrees(math.acos(cos_angle))
        
        angles["left_elbow"] = angle_between(ls, le, lw) or 0
        angles["right_elbow"] = angle_between(rs, re, rw) or 0
        
        # Hip angle
        hip_center = (lh.x + rh.x) / 2
        shoulder_center = (ls.x + rs.x) / 2
        angles["hip"] = abs(hip_center - shoulder_center) * 90
        
        # Normalize angles (0-180 range)
        for key in angles:
            if angles[key] is not None:
                angles[key] = max(0, min(180, angles[key]))
        
    except Exception as e:
        return None
    
    return angles

def extract_unity_features(landmarks):
    """Return the ordered, normalized feature vector used by MotionGuard Unity."""
    p = mp_pose.PoseLandmark

    def joint_angle(a, b, c):
        u = (a.x - b.x, a.y - b.y)
        v = (c.x - b.x, c.y - b.y)
        magnitude = math.hypot(*u) * math.hypot(*v)
        if magnitude < 0.001:
            return 0.0
        return math.degrees(math.acos(max(-1, min(1, (u[0] * v[0] + u[1] * v[1]) / magnitude)))) / 180.0

    ls, rs = landmarks[p.LEFT_SHOULDER], landmarks[p.RIGHT_SHOULDER]
    lh, rh = landmarks[p.LEFT_HIP], landmarks[p.RIGHT_HIP]
    shoulder_center = type("Point", (), {"x": (ls.x + rs.x) / 2, "y": (ls.y + rs.y) / 2})()
    hip_center = type("Point", (), {"x": (lh.x + rh.x) / 2, "y": (lh.y + rh.y) / 2})()
    vertical = type("Point", (), {"x": shoulder_center.x, "y": shoulder_center.y - 1})()
    return [
        joint_angle(landmarks[p.LEFT_ELBOW], ls, lh),
        joint_angle(landmarks[p.RIGHT_ELBOW], rs, rh),
        joint_angle(ls, landmarks[p.LEFT_ELBOW], landmarks[p.LEFT_WRIST]),
        joint_angle(rs, landmarks[p.RIGHT_ELBOW], landmarks[p.RIGHT_WRIST]),
        joint_angle(hip_center, shoulder_center, vertical),
    ]

def validate_recording(angles_list, technique_name):
    """Validate recorded data quality"""
    if len(angles_list) < MIN_FRAMES:
        return False, f"Not enough frames: {len(angles_list)}/{MIN_FRAMES}"
    
    # Check required angles
    required = QUALITY_CONFIG.get(technique_name, {}).get("required_angles", [])
    for angle_name in required:
        values = [a.get(angle_name, 0) for a in angles_list if a]
        if not values:
            return False, f"Missing angle: {angle_name}"
        
        # Check variance (shouldn't be too high or too low)
        variance = np.var(values)
        if variance > 500:  # Too much variation
            return False, f"Too much variation in {angle_name}: {variance:.1f}"
        if variance < 1:  # Not enough variation
            return False, f"Not enough variation in {angle_name}: {variance:.1f}"
    
    return True, "Quality check passed"

def record_technique(technique_name, sample_num, lock=None):
    """Record a single technique sample with validation and player lock filter"""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(f"❌ Camera not found!")
        return None
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print(f"\n🎯 Recording {technique_name} - Sample {sample_num+1}")
    print("   Get ready...")
    
    # Countdown
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)
    
    print("   🎬 RECORDING NOW! Perform the technique...")
    
    recorded_angles = []
    recorded_keypoints = []
    recorded_feature_frames = []
    visibility_history = deque(maxlen=10)
    bystander_frames_skipped = 0
    start_time = time.time()
    
    while time.time() - start_time < RECORD_DURATION:
        ret, frame = cap.read()
        if not ret:
            continue
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            if lock is not None and not lock.accepts(landmarks):
                bystander_frames_skipped += 1
                cv2.putText(frame, "BYSTANDER DETECTED - SKIPPED", (10, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 60, 255), 2)
            else:
                angles = extract_angles(landmarks, frame.shape)
                if angles:
                    recorded_angles.append(angles)
                    recorded_feature_frames.append({"values": extract_unity_features(landmarks)})
                    
                    # Extract keypoints for DTW
                    keypoints = []
                    for lm in landmarks:
                        keypoints.extend([lm.x, lm.y])
                    recorded_keypoints.append(keypoints)
                    
                    # Track visibility
                    visibility = sum([lm.visibility for lm in landmarks]) / len(landmarks)
                    visibility_history.append(visibility)
        
        # Show feedback
        cv2.putText(frame, f"Recording: {technique_name}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Frames: {len(recorded_angles)}/{MIN_FRAMES}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        cv2.putText(frame, f"Time: {int(time.time() - start_time)}s/{RECORD_DURATION}s", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        if lock is not None:
            lock.draw_overlay(frame, results.pose_landmarks.landmark if results.pose_landmarks else None)

        cv2.imshow("Record Technique", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Validate recording
    is_valid, message = validate_recording(recorded_angles, technique_name)
    if not is_valid:
        print(f"   ❌ {message}")
        return None
    
    if len(recorded_angles) < MIN_FRAMES:
        print(f"   ❌ Not enough frames: {len(recorded_angles)}/{MIN_FRAMES}")
        return None
    
    # Calculate average angles
    avg_angles = {}
    for key in recorded_angles[0].keys():
        values = [a.get(key, 0) for a in recorded_angles if a]
        avg_angles[key] = float(np.mean(values))
    
    std_angles = {}
    for key in recorded_angles[0].keys():
        values = [a.get(key, 0) for a in recorded_angles if a]
        std_angles[key] = float(np.std(values))
    
    # Average keypoints for DTW
    avg_keypoints = np.mean(recorded_keypoints, axis=0).tolist()
    
    std_angles = {}
    for key in recorded_angles[0].keys():
        values = [a.get(key, 0) for a in recorded_angles if a]
        std_angles[key] = float(np.std(values))
    
    # Average keypoints for DTW
    avg_keypoints = np.mean(recorded_keypoints, axis=0).tolist()
    
    print(f"   ✅ Quality check passed!")
    print(f"   📊 Frames: {len(recorded_angles)}")
    print(f"   📐 Angles: {avg_angles}")
    print(f"   📊 Variance: {std_angles}")
    
    return {
        "technique": technique_name,
        "sample": sample_num,
        "timestamp": datetime.now().isoformat(),
        "joint_angles": avg_angles,
        "std_angles": std_angles,
        "keypoints": avg_keypoints,
        "feature_frames": recorded_feature_frames,
        "num_frames": len(recorded_angles),
        "quality_score": 1.0 - (sum(std_angles.values()) / (len(std_angles) * 100))
    }

def main():
    """Main recording function"""
    print("=" * 70)
    print("🎯 REFERENCE DATA RECORDER - ENHANCED")
    print("=" * 70)
    print(f"Techniques: {TECHNIQUES}")
    print(f"Samples per technique: {SAMPLES_PER_TECHNIQUE}")
    print(f"Minimum frames required: {MIN_FRAMES}")
    print("=" * 70)
    print("\n📋 INSTRUCTIONS:")
    print("1. Stand in front of camera with good lighting")
    print("2. After countdown, perform the technique")
    print("3. Hold the final pose steady for 3 seconds")
    print("4. Make sure your full body is visible")
    print("5. Press 'q' to cancel recording")
    print("=" * 70)
    
    all_data = []
    successful_recordings = {t: 0 for t in TECHNIQUES}
    
    # ── PLAYER SCAN PHASE ──
    print("\n🔍 Initializing Player Scanner to prevent background passersby detection...")
    cap_scan = cv2.VideoCapture(0)
    lock = None
    if cap_scan.isOpened():
        try:
            lock = scan_for_player(cap_scan, pose, mp_pose, scan_seconds=5.0)
            print("🔒 Player successfully locked! Background passersby will be filtered out.\n")
        except Exception as e:
            print(f"⚠️ Scan failed or skipped ({e}). Proceeding without lock filter.\n")
        finally:
            cap_scan.release()
            cv2.destroyAllWindows()
    
    for technique in TECHNIQUES:
        print(f"\n📹 Recording {technique}...")
        successful = 0
        
        while successful < SAMPLES_PER_TECHNIQUE:
            input(f"\nPress ENTER to record {technique} - Sample {successful+1}")
            data = record_technique(technique, successful, lock=lock)
            
            if data:
                all_data.append(data)
                successful += 1
                successful_recordings[technique] = successful
                
                # Save immediately
                with open(f"{OUTPUT_DIR}/reference_data.json", "w") as f:
                    json.dump(all_data, f, indent=2)
                print(f"   💾 Saved sample {successful}/{SAMPLES_PER_TECHNIQUE}")
            else:
                print(f"   ⚠️ Recording failed. Retrying...")
    
    print("\n" + "=" * 70)
    print("✅ Recording complete!")
    print("=" * 70)
    print(f"Total samples: {len(all_data)}")
    for technique, count in successful_recordings.items():
        print(f"   {technique}: {count}/{SAMPLES_PER_TECHNIQUE} samples")
    print(f"Location: {OUTPUT_DIR}/reference_data.json")

if __name__ == "__main__":
    main()
