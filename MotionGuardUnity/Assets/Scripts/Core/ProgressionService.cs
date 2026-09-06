using System.Collections.Generic;
using System.Linq;

namespace MotionGuard {
    public static class ProgressionService {
        public static int PointsFor(PerformanceClass performance,int basePoints) => performance==PerformanceClass.Critical?basePoints:performance==PerformanceClass.Clean?basePoints/2:performance==PerformanceClass.Weak?basePoints/4:0;
        public static void Apply(PlayerProgress progress,AttemptRecord attempt) { progress.points+=attempt.pointsAwarded; progress.attempts.Add(attempt); if(attempt.performance==PerformanceClass.Critical&&!progress.criticalTechniqueIds.Contains(attempt.targetTechniqueId))progress.criticalTechniqueIds.Add(attempt.targetTechniqueId); }
        public static void AwardRewards(PlayerProgress progress,TechniqueCatalog catalog) {
            foreach(var id in progress.criticalTechniqueIds) AddReward(progress,"badge_critical_"+id);
            if(IsUnlocked(Tier.Amateur,progress,catalog)) AddReward(progress,"unlock_amateur_tier");
            if(IsUnlocked(Tier.Advanced,progress,catalog)) AddReward(progress,"unlock_advanced_tier");
        }
        static void AddReward(PlayerProgress progress,string id){if(!progress.unlockedRewardIds.Contains(id))progress.unlockedRewardIds.Add(id);}
        public static bool IsUnlocked(Tier tier,PlayerProgress p,TechniqueCatalog c) {
            if(tier==Tier.Beginner)return true;
            var beginner=c.techniques.Where(t=>t.tier==Tier.Beginner).Select(t=>t.id).ToList();
            if(tier==Tier.Amateur)return p.points>=c.progression.amateurPoints&&beginner.All(p.criticalTechniqueIds.Contains);
            var amateur=c.techniques.Where(t=>t.tier==Tier.Amateur).Select(t=>t.id).ToList();
            return p.points>=c.progression.advancedPoints&&amateur.All(p.criticalTechniqueIds.Contains);
        }
    }
}
