"""
TEST REFERENCE MODEL
Tests a technique against the trained reference
"""

import json
import numpy as np
import cv2
import mediapipe as mp
import math
import time

# ===== LOAD TRAINED MODEL =====
def load_model(filepath="trained_model/reference_model.json"):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Model not found: {filepath}")
        print("   Run train_reference.py first!")
        return None

# ===== DTW FUNCTION =====
def dtw_distance(seq1, seq2):
    n, m = len(seq1), len(seq2)
    if n == 0 or m == 0:
        return 9999
    dtw = np.zeros((n + 1, m + 1))
    dtw[0, :] = np.inf
    dtw[:, 0] = np.inf
    dtw[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(seq1[i-1] - seq2[j-1])
            dtw[i, j] = cost + min(dtw[i-1, j], dtw[i, j-1], dtw[i-1, j-1])
    return dtw[n, m]

def calculate_dtw_score(user_seq, ref_seq):
    if len(user_seq) == 0 or len(ref_seq) == 0:
        return 0.0
    dist = dtw_distance(user_seq, ref_seq)
    return max(0.0, min(1.0, 1.0 - (dist / 50.0)))

# ===== COSINE SIMILARITY =====
def cosine_similarity(vec1, vec2):
    if len(vec1) == 0 or len(vec2) == 0:
        return 0.0
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    dot = np.dot(v1, v2)
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (n1 * n2)))

# ===== EXTRACT ANGLES =====
def extract_joint_angles(landmarks):
    angles = {}
    try:
        ls = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        rs = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        le = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
        re = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        lw = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
        rw = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        lh = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        rh = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        
        angles["left_shoulder"] = math.degrees(math.atan2(abs(lw.x - ls.x), abs(lw.y - ls.y) + 0.001))
        angles["right_shoulder"] = math.degrees(math.atan2(abs(rw.x - rs.x), abs(rw.y - rs.y) + 0.001))
        
        def angle_between(p1, p2, p3):
            v1 = (p1.x - p2.x, p1.y - p2.y)
            v2 = (p3.x - p2.x, p3.y - p2.y)
            dot = v1[0]*v2[0] + v1[1]*v2[1]
            mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
            mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
            if mag1 == 0 or mag2 == 0:
                return 0
            return math.degrees(math.acos(max(-1, min(1, dot / (mag1 * mag2)))))
        
        angles["left_elbow"] = angle_between(ls, le, lw)
        angles["right_elbow"] = angle_between(rs, re, rw)
        
        hip_center = (lh.x + rh.x) / 2
        shoulder_center = (ls.x + rs.x) / 2
        angles["hip"] = abs(hip_center - shoulder_center) * 90
        
    except:
        pass
    return angles

# ===== TEST FUNCTION =====
def test_pose():
    """Test live pose against trained model"""
    model = load_model()
    if model is None:
        return
    
    print("=" * 60)
    print("🎯 TESTING AGAINST TRAINED MODEL")
    print("=" * 60)
    print("Available techniques:", list(model.keys()))
    print("Press 'q' to quit")
    print("=" * 60)
    
    # Initialize MediaPipe
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=0,
        min_detection_confidence=0.3,
        min_tracking_confidence=0.3
    )
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            angles = extract_joint_angles(landmarks)
            
            # Extract keypoints for DTW
            keypoints = []
            for lm in landmarks:
                keypoints.extend([lm.x, lm.y])
            
            # Test against each technique
            results_text = []
            for technique, ref in model.items():
                # Form score (Cosine Similarity)
                form_score = cosine_similarity(
                    list(angles.values()),
                    list(ref["joint_angles"].values())
                )
                
                # DTW score
                dtw_score = calculate_dtw_score(keypoints, ref["keypoints"])
                
                # Combined score
                combined = (0.5 * form_score) + (0.5 * dtw_score)
                
                results_text.append(f"{technique}: {combined*100:.0f}%")
                
                # Draw result
                y_pos = 30 + list(model.keys()).index(technique) * 30
                color = (0, 255, 0) if combined > 0.5 else (0, 0, 255)
                cv2.putText(frame, f"{technique}: {combined*100:.0f}%", 
                           (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.6, color, 2)
            
            # Draw skeleton
            mp.solutions.drawing_utils.draw_landmarks(
                frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS
            )
        
        cv2.imshow("Test Reference Model", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_pose()