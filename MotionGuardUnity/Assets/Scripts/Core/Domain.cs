using System;
using System.Collections.Generic;

namespace MotionGuard {
    public enum Tier { Beginner, Amateur, Advanced }
    public enum PerformanceClass { Miss, Weak, Clean, Critical }

    [Serializable] public class TechniqueCatalog { public List<TechniqueDefinition> techniques = new(); public ScoringSettings scoring = new(); public ProgressionSettings progression = new(); }
    [Serializable] public class TechniqueDefinition {
        public string id; public string displayName; public Tier tier; public string referencePath;
        public bool readyForEvaluation; public List<string> feedbackCues = new(); public int basePoints = 100;
    }
    [Serializable] public class ScoringSettings { public float dtwWeight = .55f; public float cosineWeight = .45f; public float maxDtwDistance = 1.25f; public float criticalThreshold = .90f; public float cleanThreshold = .72f; public float weakThreshold = .45f; }
    [Serializable] public class ProgressionSettings { public int amateurPoints = 500; public int advancedPoints = 1500; }
    [Serializable] public class FeatureFrame { public List<float> values = new(); }
    [Serializable] public class ReferenceSequence { public string techniqueId; public int featureVersion; public bool trainerApproved; public List<FeatureFrame> frames = new(); }
    [Serializable] public class PoseLandmark { public float x; public float y; public float z; public float visibility; }
    [Serializable] public class PoseFrame {
        public float timestamp;
        public List<PoseLandmark> landmarks = new();
        public string detectedTechnique = "Unknown";
        public float detectionConfidence;
    }
    [Serializable] public class AttemptRecord {
        public string attemptId; public string studySessionId; public string participantId; public string targetTechniqueId; public string recognizedTechniqueId; public string evaluatorLabel; public float timestampUnix;
        public string lightingCondition; public string framingCondition; public string cameraDistance; public string trackingIssue;
        public float dtwScore; public float formScore; public float combinedScore; public PerformanceClass performance;
        public int pointsAwarded; public float elapsedSeconds; public string poseQualityFailure;
    }
    [Serializable] public class PlayerProgress { public int points; public List<string> criticalTechniqueIds = new(); public List<string> unlockedRewardIds = new(); public List<AttemptRecord> attempts = new(); }
    public readonly struct EvaluationResult {
        public readonly string recognizedTechniqueId; public readonly float dtwScore, formScore, combinedScore; public readonly PerformanceClass performance;
        public EvaluationResult(string id, float dtw, float form, float combined, PerformanceClass p) { recognizedTechniqueId=id; dtwScore=dtw; formScore=form; combinedScore=combined; performance=p; }
    }
}
