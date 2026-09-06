# MotionGuard V1 - Continuing Development Plan

## Current baseline (6 September 2026)

The project already has a local Unity foundation: pose-quality checks, normalized pose features, DTW plus cosine scoring, points/tier logic, local JSON persistence, CSV export, basic UI hooks, and EditMode unit tests. The three Beginner techniques are configured but intentionally disabled.

The current data is **not evaluation-ready**: `reference_data/reference_data.json` contains one Punch recording only; every Unity reference is empty and unapproved; and no actual Unity MediaPipe pose callback has been connected.

## V1 definition of done

MotionGuard V1 is ready for beta testing when it can, without saving raw video:

1. Capture a single visible participant from a webcam and reject unusable framing/landmarks with a clear reason.
2. Evaluate the trainer-approved Beginner references for Controlled Straight Punch, Two-Arm High Block, and Protective Step-Back Exit using DTW (55%) and cosine similarity (45%).
3. Show the recognized technique, DTW score, form score, combined result class, appropriate feedback, and points in real time after each attempt.
4. Persist anonymized attempt metrics, participant/evaluator labels, pose-quality failures, and testing conditions; export them to CSV.
5. Enforce the specified progression: Amateur at 500 points plus Critical on all three Beginner techniques; Advanced at 1,500 points plus Critical on the Amateur technique.
6. Produce a reproducible technical-results dataset and user-acceptance dataset for the thesis evaluation.

## Ordered work plan

| Phase | Required work | Completion evidence | Status |
| --- | --- | --- | --- |
| 1. Lock the V1 data contract | Keep the version-2, 11-feature full-body vector used by `PoseMath` identical in Python recording/export and Unity evaluation. It covers shoulders, elbows, hips, knees, ankles, and torso lean. Define feature order, capture duration, minimum frames, and threshold configuration. | One documented JSON schema; fixtures validate Python-exported JSON can load in Unity. | Next |
| 2. Connect live pose input | Add a Unity-compatible MediaPipe Tasks package and an adapter that maps its 33 landmarks to `MediaPipePoseBridge.SubmitLandmarks` every frame. Build a test scene with webcam preview, bridge, runtime, and UI. | In Play Mode, webcam preview and quality status update from a real participant. | Not started |
| 3. Repair reference recording/export | Update the recorder/exporter so feature-frame extraction exactly matches Unity's feature order. Record 10 clean 3-second clips each for Punch, Block, and Escape with one qualified trainer; reject poor trials. | 30 source sequences; at least 18 valid frames each; `train_model.py` report reviewed. | Not started |
| 4. Trainer approval gate | Export the best complete sequence per Beginner technique, obtain trainer review, then set `trainerApproved: true` and corresponding `readyForEvaluation: true`. Keep higher tiers disabled. | Three reviewed reference files, enabled only after recorded approval. | Blocked by trainer recordings/approval |
| 5. Finish gameplay UI | Implement menu, technique selection, locked state, countdown, safety/framing guidance, result panel, points/reward feedback, and dashboard. Wire buttons to `MotionGuardUiController`. | A user can complete all V1 flows using only the scene UI. | Partially scaffolded |
| 6. Research-grade attempt logging | Add a study-session ID, pseudonymous participant ID, evaluator's independent ground-truth label, lighting/framing/distance category, and tracking-issue field. Keep identifiers and raw video out of the app. | CSV has every field needed by the beta-test protocol. | Missing |
| 7. Technical tests and calibration | Add unit tests for bad configuration, no approved references, invalid feature dimensions, known DTW winners, thresholds, logging, and progression. Use a small calibration set from people other than the trainer to tune thresholds before formal testing. | Passing Unity EditMode tests and documented fixed thresholds. | Partially covered |
| 8. Alpha and beta evaluation | Run alpha tests, correct defects, then collect two attempts per Beginner technique from each consented student. An evaluator labels each attempt independently. Analyse valid labelled attempts overall and by condition. | Confusion matrix, recognition accuracy, pose-rejection rate, mean similarity scores, and questionnaire results. | Not started |

## Important implementation decisions

- The currently stored reference clips must not be treated as approved data. Do not enable a technique just to test the UI; use explicitly marked development fixtures instead.
- Accuracy cannot be calculated from `targetTechniqueId == recognizedTechniqueId` alone. The target is a prompt; the beta-test accuracy denominator/numerator must use an independent evaluator's ground-truth label, excluding pose-rejected or unlabelled attempts as documented.
- Retain one full, trainer-approved sequence for each reference as the Unity DTW input. The legacy averaged Python model may support validation, but it must not replace the full DTW sequence.
- Do not add Amateur/Advanced movements or unlock their entries until their trainer-defined names, recordings, and approvals exist.
- Treat all feedback as training guidance only, not a safety guarantee or clinical assessment.

## Immediate next development slice

1. Implement and test the MediaPipe Tasks Unity adapter in a dedicated calibration scene.
2. Align the Python recorder/exporter feature vector with `PoseMath.FeatureNames`, then add a fixture-based compatibility test.
3. Extend `AttemptRecord` and CSV export with evaluator labels and environment-condition fields before any beta data collection.

This order prevents collecting references or beta data that Unity cannot evaluate consistently or that cannot support the thesis accuracy calculation.
