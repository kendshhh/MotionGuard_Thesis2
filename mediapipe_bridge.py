"""
MOTIONGUARD - MediaPipe Bridge (FIXED - No UnboundLocalError)
"""

import socket
import json
import time
import cv2
import numpy as np
import base64
import threading

# ===== CORRECT MEDIAPIPE IMPORT =====
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    print("✅ MediaPipe imported via tasks API")
except ImportError:
    import mediapipe as mp
    print("✅ MediaPipe imported standard")

# ===== CONFIGURATION =====
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
VIDEO_PORT = 5006
CAMERA_INDEX = 0
FRAME_RATE = 20
RESIZE_WIDTH = 320
JPEG_QUALITY = 70

# ===== GLOBAL VARIABLES =====
# IMPORTANT: These need to be declared as global in functions that modify them
latest_frame = None
frame_lock = threading.Lock()
running = True
video_frame_count = 0
pose_frame_count = 0

# ===== INITIALIZE MEDIAPIPE POSE =====
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

print("✅ MediaPipe Pose initialized!")

# ===== DETECT TECHNIQUE =====
def detect_technique(landmarks):
    """Detect Punch, Block, or Escape from pose landmarks"""
    try:
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
    except:
        return "Unknown", 0.0
    
    # Arm positions
    left_arm_extended = left_wrist.x > left_shoulder.x + 0.15
    right_arm_extended = right_wrist.x > right_shoulder.x + 0.15
    left_arm_raised = left_wrist.y < left_shoulder.y - 0.05
    right_arm_raised = right_wrist.y < right_shoulder.y - 0.05
    
    # Guarding (arms near face/chest)
    left_guarding = abs(left_wrist.x - left_shoulder.x) < 0.25 and left_wrist.y < left_shoulder.y
    right_guarding = abs(right_wrist.x - right_shoulder.x) < 0.25 and right_wrist.y < right_shoulder.y
    
    # Body center for escape detection
    body_center = (left_shoulder.x + right_shoulder.x) / 2
    
    # PUNCH: One arm extended, other guarding
    if (left_arm_extended and right_guarding) or (right_arm_extended and left_guarding):
        return "Punch", 0.85
    
    # BLOCK: Both arms raised and guarding
    if left_arm_raised and right_arm_raised and left_guarding and right_guarding:
        return "Block", 0.80
    
    # ESCAPE: Body off-center, arms protecting
    if abs(body_center - 0.5) > 0.1 and (left_guarding or right_guarding):
        return "Escape", 0.70
    
    return "Unknown", 0.3

def process_frame(frame):
    """Process a single frame with MediaPipe"""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)
    
    if not results.pose_landmarks:
        return None, frame
    
    # Draw landmarks
    annotated_frame = frame.copy()
    mp.solutions.drawing_utils.draw_landmarks(
        annotated_frame, 
        results.pose_landmarks, 
        mp_pose.POSE_CONNECTIONS
    )
    
    # Detect technique
    landmarks = results.pose_landmarks.landmark
    technique, confidence = detect_technique(landmarks)
    
    # Create pose data
    pose_data = {
        "timestamp": time.time(),
        "technique": technique,
        "confidence": confidence,
        "match": confidence > 0.6,
        "match_ratio": confidence,
        "match_state": "full" if confidence > 0.7 else "near" if confidence > 0.4 else "none",
        "feedback": f"Detected: {technique}",
        "keypoints": [],
        "scores": {"Punch": 0.0, "Block": 0.0, "Escape": 0.0}
    }
    
    # Add technique text to frame
    cv2.putText(annotated_frame, 
                f"{technique}: {int(confidence*100)}%",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0) if confidence > 0.6 else (0, 0, 255),
                2)
    
    return pose_data, annotated_frame

# ===== UDP SENDERS =====
def send_pose_to_unity(pose_data):
    if pose_data is None:
        return
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        message = json.dumps(pose_data)
        sock.sendto(message.encode(), (UDP_IP, UDP_PORT))
        sock.close()
        return True
    except Exception:
        return False

def send_video_to_unity(frame):
    global video_frame_count  # ← DECLARE GLOBAL
    
    if frame is None:
        return
    
    try:
        height, width = frame.shape[:2]
        new_width = RESIZE_WIDTH
        new_height = int(height * (new_width / width))
        
        new_width = new_width if new_width % 2 == 0 else new_width + 1
        new_height = new_height if new_height % 2 == 0 else new_height + 1
        
        resized = cv2.resize(frame, (new_width, new_height))
        resized = cv2.flip(resized, 1)
        
        encode_param = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
        _, jpeg = cv2.imencode('.jpg', resized, encode_param)
        
        encoded = base64.b64encode(jpeg.tobytes()).decode('utf-8')
        
        frame_data = {
            "type": "video",
            "width": new_width,
            "height": new_height,
            "data": encoded
        }
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(json.dumps(frame_data).encode(), (UDP_IP, VIDEO_PORT))
        sock.close()
        
        video_frame_count += 1
        if video_frame_count % 30 == 0:
            print(f"📤 Video frame {video_frame_count}")
        
    except Exception as e:
        pass

# ===== VIDEO CAPTURE THREAD =====
def video_capture_thread():
    global latest_frame, running  # ← DECLARE GLOBAL
    
    cap = cv2.VideoCapture(CAMERA_INDEX)
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
        time.sleep(0.033)
    
    cap.release()
    print("📷 Camera closed")

# ===== MAIN =====
def main():
    global running, pose_frame_count, video_frame_count  # ← DECLARE GLOBAL
    
    print("=" * 60)
    print("🎮 MOTIONGUARD - MediaPipe Bridge")
    print("=" * 60)
    print(f"📡 Pose on port: {UDP_PORT}")
    print(f"📡 Video on port: {VIDEO_PORT}")
    print(f"📷 Camera: {CAMERA_INDEX}")
    print(f"🔄 Frame Rate: {FRAME_RATE} FPS")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Start video capture
    video_thread = threading.Thread(target=video_capture_thread)
    video_thread.daemon = True
    video_thread.start()
    time.sleep(1)
    
    frame_delay = 1.0 / FRAME_RATE
    
    try:
        while running:
            start_time = time.time()
            
            with frame_lock:
                if latest_frame is not None:
                    frame = latest_frame.copy()
                else:
                    frame = None
            
            if frame is not None:
                # Process with MediaPipe
                pose_data, annotated_frame = process_frame(frame)
                
                if pose_data:
                    send_pose_to_unity(pose_data)
                    pose_frame_count += 1  # ← This now works because we declared global
                    if pose_frame_count % 5 == 0:
                        print(f"🎯 [{pose_frame_count}] {pose_data['technique']} "
                              f"({pose_data['confidence']*100:.0f}%)")
                
                # Send video
                send_video_to_unity(annotated_frame)
            
            elapsed = time.time() - start_time
            if elapsed < frame_delay:
                time.sleep(frame_delay - elapsed)
            
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print(f"👋 Stopped! Sent {video_frame_count} video frames, {pose_frame_count} poses")
        print("=" * 60)
        running = False

if __name__ == "__main__":
    main()