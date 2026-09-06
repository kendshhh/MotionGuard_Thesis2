using System;
using System.Collections.Generic;
using UnityEngine;

namespace MotionGuard {
    public static class PoseMath {
        public const int FeatureVersion = 2;
        // MediaPipe Pose landmark indices.
        const int Nose=0, LShoulder=11, RShoulder=12, LElbow=13, RElbow=14, LWrist=15, RWrist=16,
            LHip=23, RHip=24, LKnee=25, RKnee=26, LAnkle=27, RAnkle=28, LHeel=29, RHeel=30, LFootIndex=31, RFootIndex=32;
        // Full-body joint geometry. record_unity_reference.py must preserve this exact order.
        public static readonly string[] FeatureNames = {
            "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
            "left_hip", "right_hip", "left_knee", "right_knee",
            "left_ankle", "right_ankle", "torso_lean"
        };
        public static bool IsUsable(PoseFrame frame, out string failure) {
            failure = null;
            if (frame == null || frame.landmarks == null || frame.landmarks.Count < 33) { failure="No body detected"; return false; }
            int[] required={Nose,LShoulder,RShoulder,LElbow,RElbow,LWrist,RWrist,LHip,RHip,LKnee,RKnee,LAnkle,RAnkle,LHeel,RHeel,LFootIndex,RFootIndex};
            foreach (var index in required) if (frame.landmarks[index] == null || frame.landmarks[index].visibility < .55f) { failure="Keep your head, hands, hips, knees, and feet visible and well lit"; return false; }
            var shoulder = Distance(frame.landmarks[LShoulder], frame.landmarks[RShoulder]);
            var torso = Distance(Mid(frame.landmarks[LShoulder],frame.landmarks[RShoulder]), Mid(frame.landmarks[LHip],frame.landmarks[RHip]));
            if (shoulder < .06f || torso < .10f) { failure="Move closer and face the camera"; return false; }
            return true;
        }
        public static FeatureFrame ToFeatures(PoseFrame frame) {
            var p=frame.landmarks;
            return new FeatureFrame { values = new List<float> {
                Angle(p[LElbow],p[LShoulder],p[LHip]), Angle(p[RElbow],p[RShoulder],p[RHip]),
                Angle(p[LShoulder],p[LElbow],p[LWrist]), Angle(p[RShoulder],p[RElbow],p[RWrist]),
                Angle(p[LShoulder],p[LHip],p[LKnee]), Angle(p[RShoulder],p[RHip],p[RKnee]),
                Angle(p[LHip],p[LKnee],p[LAnkle]), Angle(p[RHip],p[RKnee],p[RAnkle]),
                Angle(p[LKnee],p[LAnkle],p[LFootIndex]), Angle(p[RKnee],p[RAnkle],p[RFootIndex]),
                Angle(Mid(p[LHip],p[RHip]), Mid(p[LShoulder],p[RShoulder]), new PoseLandmark{x=Mid(p[LShoulder],p[RShoulder]).x,y=Mid(p[LShoulder],p[RShoulder]).y-1})
            }};
        }
        static float Angle(PoseLandmark a, PoseLandmark b, PoseLandmark c) { var u=new Vector2(a.x-b.x,a.y-b.y); var v=new Vector2(c.x-b.x,c.y-b.y); return Vector2.Angle(u,v)/180f; }
        static PoseLandmark Mid(PoseLandmark a, PoseLandmark b) => new PoseLandmark {x=(a.x+b.x)/2f,y=(a.y+b.y)/2f,z=(a.z+b.z)/2f,visibility=Mathf.Min(a.visibility,b.visibility)};
        static float Distance(PoseLandmark a, PoseLandmark b) => Vector2.Distance(new Vector2(a.x,a.y),new Vector2(b.x,b.y));
    }
}
