# Repository Guidelines

## Project Structure & Module Organization

This Unity 2022.3.62f3 Windows project keeps code under `Assets/Scripts/`, organized by assembly:

- `Core/` contains motion-domain models, scoring, progression, and dashboard logic.
- `Runtime/` owns webcam, MediaPipe integration, local persistence, and runtime orchestration.
- `UI/` contains scene-facing UI controllers.
- `Tests/EditMode/` contains NUnit edit-mode tests for core behavior.
- `StreamingAssets/MotionGuard/` stores technique definitions and approved JSON reference sequences. Treat these as reviewed training data, not casual fixtures.

Unity-generated folders (`Library/`, `Temp/`, `Logs/`, and `obj/`) are local artifacts; do not edit or commit them.

## Build, Test, and Development

Open the repository root in **Unity Hub** using Unity `2022.3.62f3`, then use the Editor:

- **Play** runs the active scene for local testing.
- **Window > General > Test Runner > EditMode > Run All** executes the NUnit suite.
- **File > Build Settings > Build** produces a Windows player after the required scene(s) are included.

The project has no command-line build or lint script checked in. Add dependencies through `Packages/manifest.json` and let Unity regenerate `packages-lock.json`.

## Coding Style & Naming Conventions

Use C# with four-space indentation and same-line declaration braces, matching `Assets/Scripts`. Use `PascalCase` for public types, methods, and properties; `camelCase` for local variables, parameters, and serialized fields. Keep namespaces under `MotionGuard` (tests use `MotionGuard.Tests`). Name one primary type per file, e.g. `MotionEvaluator.cs` for `MotionEvaluator`.

Preserve assembly boundaries: code shared by UI/runtime belongs in `Core`, while Unity API or hardware-specific code belongs in `Runtime`.

## Testing Guidelines

Write NUnit edit-mode tests in `Assets/Tests/EditMode/`, named `*Tests.cs`. Name test methods as behavior and expectation, such as `EmptySequence_IsMiss`. Cover scoring thresholds, malformed input, progression rules, and data-contract changes. Run all EditMode tests before submitting; add focused tests alongside any core logic change.

## Commit & Pull Request Guidelines

This checkout has no accessible Git history, so no repository-specific commit format can be confirmed. Use concise imperative subjects, such as `Add webcam permission feedback`. Keep commits focused.

Pull requests should explain the user-visible effect, list test results, link the relevant issue when available, and include screenshots or a short recording for UI/scene changes. Call out any changes to `techniques.json` or reference JSON and confirm trainer approval before enabling evaluation data.

## Data & Privacy

Raw video must not be saved. Player metrics belong only in Unity `persistentDataPath`; do not add cloud upload or external telemetry without explicit approval.
