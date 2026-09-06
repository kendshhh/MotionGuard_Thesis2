using System.Collections.Generic;
using NUnit.Framework;

namespace MotionGuard.Tests {
    public class MotionEvaluatorTests {
        static FeatureFrame F(params float[] values)=>new FeatureFrame{values=new List<float>(values)};
        static List<FeatureFrame> S(float offset=0)=>new List<FeatureFrame>{F(.1f+offset,.2f),F(.2f+offset,.3f),F(.3f+offset,.4f)};
        [Test] public void IdenticalSequence_IsCritical(){var refs=new Dictionary<string,ReferenceSequence>{{"punch",new ReferenceSequence{trainerApproved=true,frames=S()}}};var result=MotionEvaluator.Evaluate(S(),refs,new ScoringSettings());Assert.AreEqual("punch",result.recognizedTechniqueId);Assert.AreEqual(PerformanceClass.Critical,result.performance);}
        [Test] public void EmptySequence_IsMiss(){var result=MotionEvaluator.Evaluate(new List<FeatureFrame>(),new Dictionary<string,ReferenceSequence>(),new ScoringSettings());Assert.AreEqual(PerformanceClass.Miss,result.performance);}
        [Test] public void CosineRejectsMismatchedDimensions(){Assert.AreEqual(0,MotionEvaluator.Cosine(F(1,2),F(1)));}
        [Test] public void FullBodyFeatureContract_HasElevenVersionTwoFeatures(){Assert.AreEqual(2,PoseMath.FeatureVersion);Assert.AreEqual(11,PoseMath.FeatureNames.Length);}
        [Test] public void DtwAlignsDifferentSpeeds(){var aligned=MotionEvaluator.Alignment(new List<FeatureFrame>{F(0),F(.5f),F(1)},new List<FeatureFrame>{F(0),F(0),F(.5f),F(1)});Assert.Less(aligned.distance,.01f);}
        [Test] public void InvalidReferenceFeatureDimensions_AreSkipped(){var refs=new Dictionary<string,ReferenceSequence>{{"invalid",new ReferenceSequence{trainerApproved=true,frames=new List<FeatureFrame>{F(.1f),F(.1f,.2f)}}}};var result=MotionEvaluator.Evaluate(S(),refs,new ScoringSettings());Assert.AreEqual(PerformanceClass.Miss,result.performance);}
        [Test] public void ProgressionHonorsPointsAndCriticals(){var catalog=new TechniqueCatalog{progression=new ProgressionSettings(),techniques=new List<TechniqueDefinition>{new TechniqueDefinition{id="a",tier=Tier.Beginner},new TechniqueDefinition{id="b",tier=Tier.Beginner},new TechniqueDefinition{id="c",tier=Tier.Beginner},new TechniqueDefinition{id="d",tier=Tier.Amateur}}};var p=new PlayerProgress{points=500,criticalTechniqueIds=new List<string>{"a","b","c"}};Assert.IsTrue(ProgressionService.IsUnlocked(Tier.Amateur,p,catalog));p.points=1500;p.criticalTechniqueIds.Add("d");Assert.IsTrue(ProgressionService.IsUnlocked(Tier.Advanced,p,catalog));}
        [Test] public void PointsAreClassBased(){Assert.AreEqual(100,ProgressionService.PointsFor(PerformanceClass.Critical,100));Assert.AreEqual(50,ProgressionService.PointsFor(PerformanceClass.Clean,100));Assert.AreEqual(0,ProgressionService.PointsFor(PerformanceClass.Miss,100));}
        [Test] public void DashboardAccuracyUsesEvaluatorLabels(){var progress=new PlayerProgress{attempts=new List<AttemptRecord>{new AttemptRecord{targetTechniqueId="punch",recognizedTechniqueId="block",evaluatorLabel="punch"},new AttemptRecord{targetTechniqueId="punch",recognizedTechniqueId="punch",evaluatorLabel="punch"},new AttemptRecord{targetTechniqueId="block",recognizedTechniqueId="block"}}};var summary=PerformanceDashboard.Build(progress);Assert.AreEqual(2,summary.labeledAttempts);Assert.AreEqual(.5f,summary.recognitionAccuracy,.001f);}
    }
}
