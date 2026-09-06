using System.Collections.Generic;
using System.Linq;

namespace MotionGuard {
    public class DashboardSummary { public int totalAttempts; public int validAttempts; public int labeledAttempts; public int points; public float averagePrecision; public float recognitionAccuracy; public Dictionary<string,float> averageByTechnique = new(); }
    public static class PerformanceDashboard {
        public static DashboardSummary Build(PlayerProgress progress) {
            var all=progress?.attempts??new List<AttemptRecord>(); var valid=all.Where(a=>string.IsNullOrEmpty(a.poseQualityFailure)).ToList();
            var labeled=valid.Where(a=>!string.IsNullOrWhiteSpace(a.evaluatorLabel)).ToList();
            var s=new DashboardSummary{totalAttempts=all.Count,validAttempts=valid.Count,labeledAttempts=labeled.Count,points=progress?.points??0,averagePrecision=valid.Count==0?0:valid.Average(a=>a.combinedScore),recognitionAccuracy=labeled.Count==0?0:labeled.Count(a=>a.recognizedTechniqueId==a.evaluatorLabel)/(float)labeled.Count};
            foreach(var group in valid.GroupBy(a=>a.targetTechniqueId))s.averageByTechnique[group.Key]=group.Average(a=>a.combinedScore); return s;
        }
    }
}
