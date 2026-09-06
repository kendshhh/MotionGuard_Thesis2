using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Globalization;
using System.Linq;
using UnityEngine;

namespace MotionGuard {
    public class MotionGuardRuntime : MonoBehaviour {
        [SerializeField] MediaPipePoseBridge poseBridge; [SerializeField] float captureSeconds=3f; [SerializeField] int minimumFrames=18;
        [SerializeField] string studySessionId="development"; [SerializeField] string participantId="unassigned";
        [SerializeField] string lightingCondition="unrecorded"; [SerializeField] string framingCondition="unrecorded"; [SerializeField] string cameraDistance="unrecorded";
        public TechniqueCatalog Catalog {get;private set;} public PlayerProgress Progress {get;private set;} public string Status {get;private set;} = "Read safety guidance before training.";
        public event Action<AttemptRecord,string> AttemptCompleted;
        LocalDataStore store; Dictionary<string,ReferenceSequence> references=new();
        void Awake(){store=new LocalDataStore(); Catalog=store.ReadStreaming<TechniqueCatalog>("MotionGuard/techniques.json"); Progress=store.Load<PlayerProgress>("player-progress.json"); foreach(var t in Catalog.techniques){if(!t.readyForEvaluation)continue;var r=store.ReadStreaming<ReferenceSequence>(t.referencePath); if(r!=null&&r.trainerApproved&&r.featureVersion==PoseMath.FeatureVersion&&r.frames!=null&&r.frames.Count>0)references[t.id]=r; else if(r!=null&&r.trainerApproved)Debug.LogWarning($"Reference '{t.id}' is not full-body feature version {PoseMath.FeatureVersion} and was ignored.");} }
        public bool CanSelect(TechniqueDefinition technique) => technique!=null&&technique.readyForEvaluation&&ProgressionService.IsUnlocked(technique.tier,Progress,Catalog);
        public void StartAttempt(string techniqueId){var t=Catalog.techniques.Find(x=>x.id==techniqueId); if(!CanSelect(t)){Status="This technique is locked or awaits trainer-approved reference data.";return;} StartCoroutine(Capture(t));}
        IEnumerator Capture(TechniqueDefinition target){Status="Check lighting, clear background, and full-body framing."; yield return new WaitForSeconds(2); for(int i=3;i>0;i--){Status=i.ToString();yield return new WaitForSeconds(1);} Status="Perform the technique";var sequence=new List<FeatureFrame>();string failure=null;var start=Time.unscaledTime;
            while(Time.unscaledTime-start<captureSeconds){if(poseBridge==null||!poseBridge.HasFreshFrame){failure="No body detected";}else if(PoseMath.IsUsable(poseBridge.LatestFrame,out var reason)){sequence.Add(PoseMath.ToFeatures(poseBridge.LatestFrame));}else failure=reason;yield return null;}
            if(sequence.Count<minimumFrames){Status=failure??"Insufficient valid movement data. Try again.";CompleteFailure(target,start,Status);yield break;}
            var result=MotionEvaluator.Evaluate(sequence,references,Catalog.scoring);var points=ProgressionService.PointsFor(result.performance,target.basePoints);var record=CreateAttemptRecord(target.id,start,result,points);
            ProgressionService.Apply(Progress,record);ProgressionService.AwardRewards(Progress,Catalog);store.Save("player-progress.json",Progress);var cue=Feedback(target,result);Status=$"{result.performance}: {result.combinedScore:P0}. {cue}";AttemptCompleted?.Invoke(record,cue);
        }
        AttemptRecord CreateAttemptRecord(string targetId,float start,EvaluationResult result,int points,string failure=null) => new AttemptRecord { attemptId=Guid.NewGuid().ToString("N"),studySessionId=studySessionId,participantId=participantId,targetTechniqueId=targetId,recognizedTechniqueId=result.recognizedTechniqueId,evaluatorLabel="",timestampUnix=DateTimeOffset.UtcNow.ToUnixTimeSeconds(),lightingCondition=lightingCondition,framingCondition=framingCondition,cameraDistance=cameraDistance,trackingIssue=failure,dtwScore=result.dtwScore,formScore=result.formScore,combinedScore=result.combinedScore,performance=result.performance,pointsAwarded=points,elapsedSeconds=Time.unscaledTime-start,poseQualityFailure=failure };
        void CompleteFailure(TechniqueDefinition t,float start,string why){var r=CreateAttemptRecord(t.id,start,new EvaluationResult(null,0,0,0,PerformanceClass.Miss),0,why);ProgressionService.Apply(Progress,r);store.Save("player-progress.json",Progress);AttemptCompleted?.Invoke(r,why);}
        public bool SetEvaluatorLabel(string attemptId,string evaluatorLabel) { if(string.IsNullOrWhiteSpace(evaluatorLabel)||Catalog==null||!Catalog.techniques.Any(t=>t.id==evaluatorLabel))return false; var attempt=Progress?.attempts?.Find(a=>a.attemptId==attemptId); if(attempt==null)return false; attempt.evaluatorLabel=evaluatorLabel; store.Save("player-progress.json",Progress); return true; }
        public string ExportAnonymizedAttemptCsv() { var path=Path.Combine(Application.persistentDataPath,"motionguard-attempts.csv"); var lines=new List<string>{"attempt_id,study_session_id,participant_id,target,recognized,evaluator_label,timestamp,lighting,framing,camera_distance,tracking_issue,dtw_score,form_score,combined_score,performance,points,elapsed_seconds,pose_failure"}; foreach(var a in Progress.attempts) lines.Add(string.Join(",",Csv(a.attemptId),Csv(a.studySessionId),Csv(a.participantId),Csv(a.targetTechniqueId),Csv(a.recognizedTechniqueId),Csv(a.evaluatorLabel),a.timestampUnix.ToString(CultureInfo.InvariantCulture),Csv(a.lightingCondition),Csv(a.framingCondition),Csv(a.cameraDistance),Csv(a.trackingIssue),Number(a.dtwScore),Number(a.formScore),Number(a.combinedScore),Csv(a.performance.ToString()),a.pointsAwarded.ToString(CultureInfo.InvariantCulture),Number(a.elapsedSeconds),Csv(a.poseQualityFailure))); File.WriteAllLines(path,lines); return path; }
        static string Csv(string value)=>"\""+(value??"").Replace("\"","\"\"")+"\"";
        static string Number(float value)=>value.ToString("0.####",CultureInfo.InvariantCulture);
        string Feedback(TechniqueDefinition target,EvaluationResult result){if(result.performance==PerformanceClass.Critical)return "Excellent control.";if(result.recognizedTechniqueId!=target.id)return "The movement most closely matched another technique; review the demonstration.";return target.feedbackCues!=null&&target.feedbackCues.Count>0?target.feedbackCues[0]:"Repeat slowly with controlled form.";}
    }
}
