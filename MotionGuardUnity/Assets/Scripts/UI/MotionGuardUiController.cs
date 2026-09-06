using TMPro;
using UnityEngine;

namespace MotionGuard {
    public class MotionGuardUiController : MonoBehaviour {
        [SerializeField] MotionGuardRuntime runtime; [SerializeField] TMP_Text statusText,pointsText,resultText,dashboardText;
        void OnEnable(){if(runtime!=null)runtime.AttemptCompleted+=ShowResult;}
        void OnDisable(){if(runtime!=null)runtime.AttemptCompleted-=ShowResult;}
        void Update(){if(runtime==null)return;if(statusText)statusText.text=runtime.Status;if(pointsText)pointsText.text=$"Points: {runtime.Progress?.points??0}";}
        public void BeginTechnique(string id)=>runtime.StartAttempt(id);
        public void ShowDashboard(){var s=PerformanceDashboard.Build(runtime.Progress);if(dashboardText)dashboardText.text=$"Attempts: {s.totalAttempts}\nValid: {s.validAttempts}\nEvaluator-labeled: {s.labeledAttempts}\nAverage precision: {s.averagePrecision:P0}\nRecognition accuracy: {(s.labeledAttempts==0?"Pending labels":s.recognitionAccuracy.ToString("P0"))}\nRewards: {runtime.Progress.unlockedRewardIds.Count}";}
        public void ExportTechnicalResults(){runtime.ExportAnonymizedAttemptCsv();}
        void ShowResult(AttemptRecord a,string feedback){if(resultText)resultText.text=$"{a.performance}  {a.combinedScore:P0}\n{feedback}\n+{a.pointsAwarded} points";}
    }
}
