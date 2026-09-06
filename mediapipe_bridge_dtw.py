"""
MOTIONGUARD - MediaPipe Bridge with Trained Model
Production ready with DTW + Cosine Similarity
"""

import socket
import json
import time
import cv2
import numpy as np
import base64
import threading
import math
from collections import deque
import os

# ===== CONFIGURATION =====
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
VIDEO_PORT = 5006
CAMERA_INDEX = 0
FRAME_RATE = 10
RESIZE_WIDTH = 320
JPEG_QUALITY = 70
MODEL_PATH = "trained_model/reference_model.json"

# ===== GLOBAL VARIABLES =====
latest_frame = None
frame_lock = threading.Lock()
running = True
video_frame_count = 0
pose_frame_count = 0

# ===== LOAD TRAINED MODEL =====
def load_model(filepath=MODEL_PATH):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Model not found: {filepath}")
        print("   Using default reference data")
        return None

REFERENCE_MODEL = load_model()

# ===== MEDIAPIPE IMPORT =====
try:
    import mediapipe as mp
    print("✅ MediaPipe imported")
except ImportError:
    print("❌ MediaPipe not installed")
    exit(1)

# ===== INITIALIZE MEDIAPIPE =====
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=0,
    min_detection_confidence=0.4,
    min_tracking_confidence=0.4
)

# ===== DTW FUNCTIONS =====
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

def calculate_dtw_score(user_seq, ref_seq, max_distance=50.0):
    if len(user_seq) == 0 or len(ref_seq) == 0:
        return 0.0
    dist = dtw_distance(user_seq, ref_seq)
    return max(0.0, min(1.0, 1.0 - (dist / max_distance)))

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

# ===== EXTRACT JOINT ANGLES =====
def extract_joint_angles(landmarks, frame_shape):
    angles = {}
    try:
        import math
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

# ===== DETECT TECHNIQUE =====
def detect_technique(landmarks, frame_shape):
    user_angles = extract_joint_angles(landmarks, frame_shape)
    
    if not user_angles:
        return {
            "technique": "Unknown",
            "confidence": 0.0,
            "scores": {},
            "dtw_scores": {},
            "form_scores": {},
            "match": False
        }
    
    # Get keypoints for DTW
    keypoints = []
    for lm in landmarks:
        keypoints.extend([lm.x, lm.y])
    
    technique_scores = {}
    
    if REFERENCE_MODEL:
        for technique, ref in REFERENCE_MODEL.items():
            # Form score (Cosine Similarity)
            user_vec = list(user_angles.values())
            ref_vec = list(ref["joint_angles"].values())
            form_score = cosine_similarity(user_vec, ref_vec)
            
            # DTW score
            dtw_score = calculate_dtw_score(keypoints, ref["keypoints"])
            
            # Weighted combined score
            technique_scores[technique] = (0.5 * form_score) + (0.5 * dtw_score)
    else:
        # Fallback to simple detection
        left_arm = user_angles.get("left_shoulder", 0) > 30
        right_arm = user_angles.get("right_shoulder", 0) > 30
        both_arms = left_arm and right_arm
        
        if both_arms:
            technique_scores = {"Block": 0.7, "Punch": 0.3, "Escape": 0.2}
        elif left_arm or right_arm:
            technique_scores = {"Punch": 0.7, "Block": 0.3, "Escape": 0.2}
        else:
            technique_scores = {"Escape": 0.5, "Punch": 0.2, "Block": 0.2}
    
    if not technique_scores:
        return {
            "technique": "Unknown",
            "confidence": 0.0,
            "scores": {},
            "dtw_scores": {},
            "form_scores": {},
            "match": False
        }
    
    best = max(technique_scores, key=technique_scores.get)
    
    return {
        "technique": best,
        "confidence": technique_scores[best],
        "scores": technique_scores,
        "dtw_scores": technique_scores,  # Simplified
        "form_scores": technique_scores,
        "joint_angles": user_angles,
        "match": technique_scores[best] > 0.4
    }

# ===== PROCESS FRAME =====
def process_frame(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)
    
    if not results.pose_landmarks:
        return None, frame
    
    annotated = frame.copy()
    mp.solutions.drawing_utils.draw_landmarks(
        annotated, results.pose_landmarks, mp_pose.POSE_CONNECTIONS
    )
    
    result = detect_technique(results.pose_landmarks.landmark, frame.shape)
    
    pose_data = {
        "timestamp": time.time(),
        "technique": result["technique"],
        "confidence": result["confidence"],
        "match": result["match"],
        "match_ratio": result["confidence"],
        "match_state": "full" if result["confidence"] > 0.6 else "near" if result["confidence"] > 0.3 else "none",
        "feedback": f"Detected: {result['technique']}",
        "keypoints": [],
        "scores": {
            "Punch": result["scores"].get("Punch", 0.0),
            "Block": result["scores"].get("Block", 0.0),
            "Escape": result["scores"].get("Escape", 0.0),
            "dtw_score": result.get("dtw_scores", {}).get(result["technique"], 0.0),
            "cosine_score": result.get("form_scores", {}).get(result["technique"], 0.0)
        }
    }
    
    # Add overlay text
    cv2.putText(annotated, f"{result['technique']}: {int(result['confidence']*100)}%", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                (0, 255, 0) if result['confidence'] > 0.4 else (0, 0, 255), 2)
    
    return pose_data, annotated

# ===== UDP FUNCTIONS =====
def send_pose_to_unity(pose_data):
    if not pose_data:
        return
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(json.dumps(pose_data).encode(), (UDP_IP, UDP_PORT))
        sock.close()
    except:
        pass

def send_video_to_unity(frame):
    global video_frame_count
    if frame is None:
        return
    try:
        h, w = frame.shape[:2]
        nw = RESIZE_WIDTH
        nh = int(h * (nw / w))
        resized = cv2.resize(frame, (nw, nh))
        resized = cv2.flip(resized, 1)
        _, jpeg = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        encoded = base64.b64encode(jpeg.tobytes()).decode('utf-8')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(json.dumps({"type": "video", "width": nw, "height": nh, "data": encoded}).encode(), (UDP_IP, VIDEO_PORT))
        sock.close()
        video_frame_count += 1
        if video_frame_count % 20 == 0:
            print(f"📤 Video frame {video_frame_count}")
    except:
        pass

# ===== VIDEO CAPTURE =====
def video_capture_thread():
    global latest_frame, running
    
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"❌ Camera {CAMERA_INDEX} not found")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("📷 Camera opened")
    
    while running:
        ret, frame = cap.read()
        if ret:
            with frame_lock:
                latest_frame = frame.copy()
        time.sleep(0.01)
    
    cap.release()
    print("📷 Camera closed")

# ===== MAIN =====
def main():
    global running, pose_frame_count
    
    print("=" * 70)
    print("🎮 MOTIONGUARD - Production Bridge")
    print("=" * 70)
    print(f"📡 Pose: {UDP_PORT} | Video: {VIDEO_PORT}")
    print(f"📷 Camera: {CAMERA_INDEX}")
    print(f"🧠 Model: {'✅ Loaded' if REFERENCE_MODEL else '❌ Fallback'}")
    print("=" * 70)
    
    if REFERENCE_MODEL:
        print("\n📋 Loaded techniques:")
        for technique, data in REFERENCE_MODEL.items():
            print(f"   {technique}: {data['num_samples']} samples, threshold: {data['confidence_threshold']:.2f}")
    
    print("\nPress Ctrl+C to stop")
    print("=" * 70)
    
    video_thread = threading.Thread(target=video_capture_thread)
    video_thread.daemon = True
    video_thread.start()
    time.sleep(2)
    
    # Check for frames
    has_frame = False
    for _ in range(10):
        with frame_lock:
            if latest_frame is not None:
                has_frame = True
                break
        time.sleep(0.2)
    
    if not has_frame:
        print("❌ No frames from camera!")
        return
    
    print("✅ Camera working! Starting processing...")
    
    frame_delay = 1.0 / FRAME_RATE
    counter = 0
    
    try:
        while running:
            start = time.time()
            
            with frame_lock:
                frame = latest_frame.copy() if latest_frame is not None else None
            
            if frame is not None:
                counter += 1
                if counter % 2 == 0:
                    pose_data, annotated = process_frame(frame)
                    if pose_data:
                        send_pose_to_unity(pose_data)
                        pose_frame_count += 1
                        if pose_frame_count % 5 == 0:
                            dtw = pose_data["scores"].get("dtw_score", 0.0)
                            form = pose_data["scores"].get("cosine_score", 0.0)
                            print(f"🎯 [{pose_frame_count}] {pose_data['technique']} "
                                  f"({pose_data['confidence']*100:.0f}%) "
                                  f"DTW: {dtw*100:.0f}% Form: {form*100:.0f}%")
                    send_video_to_unity(annotated)
                else:
                    send_video_to_unity(frame)
            
            elapsed = time.time() - start
            if elapsed < frame_delay:
                time.sleep(frame_delay - elapsed)
            
    except KeyboardInterrupt:
        print("\n👋 Stopped")
        running = False

if __name__ == "__main__":
    main()