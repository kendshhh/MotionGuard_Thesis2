using System;
using System.Collections.Generic;
using UnityEngine;

namespace MotionGuard {
    public static class MotionEvaluator {
        public static EvaluationResult Evaluate(List<FeatureFrame> attempt, Dictionary<string, ReferenceSequence> references, ScoringSettings settings) {
            if (attempt == null || attempt.Count == 0 || references == null || settings == null || !IsValidSequence(attempt)) return new EvaluationResult(null,0,0,0,PerformanceClass.Miss);
            string winner=null; float best=float.NegativeInfinity, bestDtw=0, bestForm=0;
            foreach (var pair in references) {
                if (pair.Value == null || !pair.Value.trainerApproved || pair.Value.frames == null || pair.Value.frames.Count == 0 || !IsValidSequence(pair.Value.frames)) continue;
                if (attempt[0].values.Count != pair.Value.frames[0].values.Count) continue;
                var path = Alignment(attempt,pair.Value.frames); var distance=path.distance; var dtw=Mathf.Clamp01(1f-distance/settings.maxDtwDistance);
                var form=MeanCosine(attempt,pair.Value.frames,path.indices); var combined=dtw*settings.dtwWeight+form*settings.cosineWeight;
                if (combined>best) { winner=pair.Key; best=combined; bestDtw=dtw; bestForm=form; }
            }
            return winner==null ? new EvaluationResult(null,0,0,0,PerformanceClass.Miss) : new EvaluationResult(winner,bestDtw,bestForm,best,Classify(best,settings));
        }
        public static PerformanceClass Classify(float score, ScoringSettings s) => score>=s.criticalThreshold?PerformanceClass.Critical:score>=s.cleanThreshold?PerformanceClass.Clean:score>=s.weakThreshold?PerformanceClass.Weak:PerformanceClass.Miss;
        public static (float distance,List<(int,int)> indices) Alignment(List<FeatureFrame> a,List<FeatureFrame> b) {
            if (!IsValidSequence(a) || !IsValidSequence(b) || a[0].values.Count != b[0].values.Count) return (float.PositiveInfinity,new List<(int,int)>());
            var d=new float[a.Count+1,b.Count+1]; for(int i=0;i<=a.Count;i++) for(int j=0;j<=b.Count;j++) d[i,j]=float.PositiveInfinity; d[0,0]=0;
            for(int i=1;i<=a.Count;i++) for(int j=1;j<=b.Count;j++) d[i,j]=Cost(a[i-1],b[j-1])+Mathf.Min(d[i-1,j],Mathf.Min(d[i,j-1],d[i-1,j-1]));
            var path=new List<(int,int)>(); for(int i=a.Count,j=b.Count;i>0&&j>0;) { path.Add((i-1,j-1)); if(d[i-1,j-1]<=d[i-1,j]&&d[i-1,j-1]<=d[i,j-1]) {i--;j--;} else if(d[i-1,j]<=d[i,j-1]) i--; else j--; } path.Reverse(); return (d[a.Count,b.Count]/Mathf.Max(1,path.Count),path);
        }
        public static float Cosine(FeatureFrame a,FeatureFrame b) { if(a.values.Count!=b.values.Count||a.values.Count==0)return 0; float dot=0,aa=0,bb=0; for(int i=0;i<a.values.Count;i++){dot+=a.values[i]*b.values[i];aa+=a.values[i]*a.values[i];bb+=b.values[i]*b.values[i];} return aa==0||bb==0?0:Mathf.Clamp01(dot/Mathf.Sqrt(aa*bb)); }
        static float MeanCosine(List<FeatureFrame> a,List<FeatureFrame>b,List<(int,int)>path){float total=0;foreach(var p in path)total+=Cosine(a[p.Item1],b[p.Item2]);return path.Count==0?0:total/path.Count;}
        static float Cost(FeatureFrame a,FeatureFrame b){if(a.values.Count!=b.values.Count)return 1;float total=0;for(int i=0;i<a.values.Count;i++)total+=Mathf.Abs(a.values[i]-b.values[i]);return total/a.values.Count;}
        static bool IsValidSequence(List<FeatureFrame> sequence) {
            if (sequence == null || sequence.Count == 0 || sequence[0] == null || sequence[0].values == null || sequence[0].values.Count == 0) return false;
            var dimensions = sequence[0].values.Count;
            foreach (var frame in sequence) if (frame == null || frame.values == null || frame.values.Count != dimensions) return false;
            return true;
        }
    }
}
