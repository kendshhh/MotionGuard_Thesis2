"""Export the best full-sequence trainer recording for each MotionGuard Unity technique.

Use only after recording multiple trainer trials with record_reference.py. This tool never
marks output approved; formal trainer review is still required.
"""
import argparse
import json
import math
from pathlib import Path


FEATURE_COUNT = 11
MIN_FRAMES = 18


def has_valid_feature_frames(frames, allowed_counts=(5, 11)):
    if not isinstance(frames, list) or len(frames) < MIN_FRAMES:
        return False
    for frame in frames:
        values = frame.get("values") if isinstance(frame, dict) else None
        if not isinstance(values, list) or len(values) not in allowed_counts:
            return False
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values):
            return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="reference_data/reference_data.json")
    parser.add_argument("--output-dir", default="MotionGuardUnity/Assets/StreamingAssets/MotionGuard/references")
    parser.add_argument("--techniques", nargs="+", default=["Punch", "Block", "Escape"])
    args = parser.parse_args()
    with open(args.input, encoding="utf-8") as stream:
        recordings = json.load(stream)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for technique in args.techniques:
        candidates = [
            item for item in recordings
            if item.get("technique") == technique
            and has_valid_feature_frames(item.get("feature_frames"))
        ]
        if not candidates:
            print(f"Skipped {technique}: no valid full-sequence recording found")
            continue
        best = max(candidates, key=lambda item: item.get("quality_score", 0))
        filename = technique.lower().replace(" ", "_") + ".json"
        payload = {
            "techniqueId": filename.removesuffix(".json"),
            "featureVersion": 2,
            "trainerApproved": False,
            "frames": best["feature_frames"]
        }
        with open(output_dir / filename, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
        print(f"Exported {technique}: {len(payload['frames'])} frames to {filename}; approval remains false")


if __name__ == "__main__":
    main()
