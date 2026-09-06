"""
MOTIONGUARD - Unity Connection Test (FIXED CAMERA)
"""

import socket
import json
import time
import cv2
import numpy as np
import base64
import threading
import math
import sys

# ===== MEDIAPIPE IMPORT =====
try:
    import mediapipe as mp
    print("✅ MediaPipe imported")
except ImportError:
    print("❌ MediaPipe not installed")
    print("   Run: pip install mediapipe")
    sys.exit(1)

# ===== CONFIGURATION =====
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
VIDEO_PORT = 5006
CAMERA_INDEX = 0  # Change to 1, 2, etc. if needed
FRAME_RATE = 15
RESIZE_WIDTH = 320
JPEG_QUALITY = 70

# ===== GLOBAL VARIABLES =====
latest_frame = None
frame_lock = threading.Lock()
running = True
video_frame_count = 0
pose_frame_count = 0
camera_ready = False

# ===== INITIALIZE MEDIAPIPE =====
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=0,
    min_detection_confidence=0.4,
    min_tracking_confidence=0.4
)

# ===== FIND WORKING CAMERA =====
def find_working_camera():
    """Find first working camera"""
    print("🔍 Searching for camera...")
    for i in range(5):
        # Try with DirectShow first
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                cap.release()
                print(f"✅ Found working camera: index {i}")
                return i
        cap.release()
    
    # Try without backend
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                cap.release()
                print(f"✅ Found working camera: index {i}")
                return i
        cap.release()
    
    print("❌ No working camera found!")
    return None

# Try to find camera automatically
AUTO_CAMERA = find_working_camera()
if AUTO_CAMERA is not None:
    CAMERA_INDEX = AUTO_CAMERA
else:
    print(f"⚠️ Using default camera index: {CAMERA_INDEX}")

# ===== TECHNIQUE DETECTION =====
def detect_technique_simple(landmarks, frame_shape):
    try:
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        
        left_arm_extended = left_wrist.x > left_shoulder.x + 0.1
        right_arm_extended = right_wrist.x > right_shoulder.x + 0.1
        left_arm_raised = left_wrist.y < left_shoulder.y - 0.05
        right_arm_raised = right_wrist.y < right_shoulder.y - 0.05
        left_guarding = abs(left_wrist.x - left_shoulder.x) < 0.2 and left_wrist.y < left_shoulder.y
        right_guarding = abs(right_wrist.x - right_shoulder.x) < 0.2 and right_wrist.y < right_shoulder.y
        
        scores = {"Punch": 0.0, "Block": 0.0, "Escape": 0.0}
        
        if (left_arm_extended and right_guarding) or (right_arm_extended and left_guarding):
            scores["Punch"] = 0.85
            scores["Block"] = 0.2
            scores["Escape"] = 0.15
        elif left_arm_raised and right_arm_raised and left_guarding and right_guarding:
            scores["Block"] = 0.80
            scores["Punch"] = 0.2
            scores["Escape"] = 0.15
        else:
            scores["Punch"] = 0.2
            scores["Block"] = 0.2
            scores["Escape"] = 0.2
        
        best = max(scores, key=scores.get)
        confidence = scores[best]
        
        return {
            "technique": best,
            "confidence": confidence,
            "scores": scores,
            "match": confidence > 0.4
        }
    except:
        return {"technique": "Unknown", "confidence": 0.0, "scores": {}, "match": False}

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
    
    result = detect_technique_simple(results.pose_landmarks.landmark, frame.shape)
    
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
            "dtw_score": result["confidence"] * 0.8,
            "cosine_score": result["confidence"] * 0.85
        }
    }
    
    cv2.putText(annotated, f"{result['technique']}: {int(result['confidence']*100)}%", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                (0, 255, 0) if result["confidence"] > 0.4 else (0, 0, 255), 2)
    cv2.putText(annotated, "TEST MODE - No Training", (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    return pose_data, annotated

# ===== UDP SENDERS =====
def send_pose_to_unity(pose_data):
    if pose_data is None:
        return
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(json.dumps(pose_data).encode(), (UDP_IP, UDP_PORT))
        sock.close()
        return True
    except:
        return False

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
    global latest_frame, running, camera_ready
    
    print("📷 Opening camera...")
    
    # Try different backends
    backends = [
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_MSMF, "Media Foundation"),
        (cv2.CAP_ANY, "Auto")
    ]
    
    cap = None
    for backend, name in backends:
        cap = cv2.VideoCapture(CAMERA_INDEX, backend)
        if cap.isOpened():
            print(f"   ✅ {name} backend works!")
            break
        cap.release()
        cap = None
    
    if cap is None:
        print(f"❌ Camera {CAMERA_INDEX} not found")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print(f"📷 Camera opened!")
    print(f"   Resolution: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
    
    camera_ready = True
    frame_count = 0
    
    while running:
        ret, frame = cap.read()
        if ret:
            with frame_lock:
                latest_frame = frame.copy()
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"📷 Captured {frame_count} frames")
        else:
            time.sleep(0.01)
    
    cap.release()
    print("📷 Camera closed")

# ===== MAIN =====
def main():
    global running, pose_frame_count, latest_frame, camera_ready
    
    print("=" * 70)
    print("🎮 MOTIONGUARD - Unity Test")
    print("=" * 70)
    print(f"📡 Pose: {UDP_PORT} | Video: {VIDEO_PORT}")
    print(f"📷 Camera: {CAMERA_INDEX}")
    print(f"🧠 Mode: No Training Required")
    print("=" * 70)
    print("Press Ctrl+C to stop")
    print("=" * 70)
    
    # Start video capture
    video_thread = threading.Thread(target=video_capture_thread)
    video_thread.daemon = True
    video_thread.start()
    
    # Wait for camera
    print("⏳ Waiting for camera...")
    time.sleep(3)
    
    if not camera_ready:
        print("❌ Camera not ready!")
        print("   Try changing CAMERA_INDEX")
        return
    
    # Check for frames
    for i in range(10):
        with frame_lock:
            if latest_frame is not None:
                break
        time.sleep(0.2)
    
    if latest_frame is None:
        print("❌ No frames from camera!")
        print("   Try changing CAMERA_INDEX")
        print("   Close other apps using camera (Zoom, OBS, etc.)")
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
                            print(f"🎯 [{pose_frame_count}] {pose_data['technique']} "
                                  f"({pose_data['confidence']*100:.0f}%)")
                    send_video_to_unity(annotated)
                else:
                    send_video_to_unity(frame)
            
            elapsed = time.time() - start
            if elapsed < frame_delay:
                time.sleep(frame_delay - elapsed)
            
    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        print(f"👋 Stopped! Sent {video_frame_count} video frames")
        print("=" * 70)
        running = False

if __name__ == "__main__":
    main()