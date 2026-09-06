# MotionGuard Unity V1

This is a Windows desktop Unity foundation for MotionGuard. It is intentionally local-only and does not use the legacy Python-to-Unity UDP bridge.

## Setup

1. Open `MotionGuardUnity` in Unity 2022.3.62f3.
2. Install a Unity-compatible MediaPipe Tasks package and make its pose-landmarker callback call `MediaPipePoseBridge.SubmitLandmarks` once per frame. The bridge is package-independent so the project remains compilable until the package is added.
3. Create a scene with `MotionGuardRuntime`, `WebcamPreview`, `MediaPipePoseBridge`, and UI controls wired to `MotionGuardUiController`.
4. Replace every placeholder reference file in `Assets/StreamingAssets/MotionGuard/references` with a qualified trainer's complete frame sequence before enabling formal evaluation.

Raw video is never saved. Player metrics are saved under Unity's `persistentDataPath`.

## Data contract

`techniques.json` controls tiers, scoring, reward values, feedback, and reference file paths. Each reference sequence has ordered `frames`; every frame has ordered normalized feature values. The feature order is documented in `MotionEvaluator.FeatureNames`.

The three seeded Beginner entries are placeholders for the current technique names only, not approved reference data. The remaining names must be trainer-approved before data collection.

## Trainer reference workflow

Use `record_reference.py` to capture multiple full-sequence trials. Then run `prepare_unity_references.py` to export the highest-quality complete trial for Punch, Block, and Escape into this Unity project. The export remains disabled until a trainer reviews it and explicitly sets both approval flags. See `../MOTIONGUARD_TECHNIQUE_BENCHMARK.md` for the approved working names and recording protocol.
