"""
TRAIN REFERENCE MODEL - ENHANCED
With cross-validation and accuracy metrics and CSV reporting
"""

import csv
import datetime
import json
import numpy as np
import os
import random
import sys
from collections import defaultdict

# Ensure stdout handles UTF-8 on Windows consoles without crashing on emojis
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FEATURE_ORDER = ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "hip"]

CSV_HEADERS = [
    "run_id",
    "timestamp",
    "technique",
    "samples_count",
    "cv_folds",
    "mean_accuracy",
    "mean_accuracy_pct",
    "std_accuracy",
    "min_accuracy",
    "max_accuracy",
    "confidence_threshold",
    "quality_score",
    "ref_sequence_frames",
    "status"
]

FOLD_CSV_HEADERS = [
    "run_id",
    "timestamp",
    "technique",
    "fold_index",
    "fold_accuracy",
    "fold_accuracy_pct"
]

def ordered_angle_vector(angles):
    """Keep model vectors deterministic even when JSON key order differs."""
    return [float(angles.get(name, 0.0)) for name in FEATURE_ORDER]

def load_reference_data(filepath="reference_data/reference_data.json"):
    """Load recorded reference data"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        print("   Run record_reference.py first!")
        return None

def cross_validate(data, technique_name, k_folds=3):
    """Perform k-fold cross-validation with detailed fold metrics"""
    samples = [d for d in data if d["technique"] == technique_name]
    if len(samples) < k_folds:
        print(f"   ⚠️ Not enough samples for {k_folds}-fold validation (need at least {k_folds}, got {len(samples)})")
        return None
    
    # Shuffle samples deterministically
    random.Random(42).shuffle(samples)
    fold_size = len(samples) // k_folds
    
    accuracies = []
    
    for fold in range(k_folds):
        # Split data
        test_start = fold * fold_size
        test_end = test_start + fold_size if fold < k_folds - 1 else len(samples)
        test_samples = samples[test_start:test_end]
        train_samples = samples[:test_start] + samples[test_end:]
        
        if len(train_samples) == 0 or len(test_samples) == 0:
            continue
        
        # Train on train_samples
        avg_angles = defaultdict(list)
        for sample in train_samples:
            for key, value in sample["joint_angles"].items():
                avg_angles[key].append(value)
        
        reference = {}
        for key, values in avg_angles.items():
            reference[key] = float(np.mean(values))
        
        # Test on test_samples
        scores = []
        for test_sample in test_samples:
            score = cosine_similarity(
                ordered_angle_vector(test_sample["joint_angles"]),
                ordered_angle_vector(reference)
            )
            scores.append(score)
        
        avg_score = float(np.mean(scores))
        accuracies.append(avg_score)
    
    if accuracies:
        return {
            "mean_accuracy": float(np.mean(accuracies)),
            "std_accuracy": float(np.std(accuracies)),
            "min_accuracy": float(np.min(accuracies)),
            "max_accuracy": float(np.max(accuracies)),
            "fold_accuracies": [float(a) for a in accuracies],
            "folds": len(accuracies)
        }
    return None

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity"""
    if len(vec1) == 0 or len(vec2) == 0:
        return 0.0
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    dot = np.dot(v1, v2)
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (n1 * n2)))

def process_technique_data(data, technique_name):
    """Process all samples for a technique with validation"""
    samples = [d for d in data if d["technique"] == technique_name]
    
    if len(samples) == 0:
        return None
    
    print(f"   📊 Processing {len(samples)} samples for {technique_name}")
    
    # Cross-validation
    cv_results = cross_validate(data, technique_name)
    if cv_results:
        print(f"   📊 Cross-validation: {cv_results['mean_accuracy']*100:.1f}% (±{cv_results['std_accuracy']*100:.1f}%)")
    
    # Average all joint angles
    avg_angles = defaultdict(list)
    for sample in samples:
        for key, value in sample["joint_angles"].items():
            avg_angles[key].append(value)
    
    final_angles = {}
    for key, values in avg_angles.items():
        final_angles[key] = float(np.mean(values))
    
    # Standard deviation for confidence
    std_angles = {}
    for key, values in avg_angles.items():
        std_angles[key] = float(np.std(values)) if len(values) > 1 else 0.1
    
    # Average keypoints for DTW
    all_keypoints = [sample["keypoints"] for sample in samples]
    final_keypoints = np.mean(all_keypoints, axis=0).tolist()
    
    # Calculate average quality score
    quality_scores = [sample.get("quality_score", 0.5) for sample in samples]
    avg_quality = np.mean(quality_scores)

    # Preserve a complete high-quality sequence for the Unity/DTW workflow.
    # Legacy averaged values above are retained only for existing Python bridge compatibility.
    sequence_candidates = [sample for sample in samples if len(sample.get("feature_frames", [])) >= 18]
    best_sequence = max(sequence_candidates, key=lambda sample: sample.get("quality_score", 0.0)).get("feature_frames", []) if sequence_candidates else []
    
    return {
        "technique": technique_name,
        "joint_angles": final_angles,
        "std_angles": std_angles,
        "keypoints": final_keypoints,
        "num_samples": len(samples),
        "confidence_threshold": max(0.4, 1.0 - (np.mean(list(std_angles.values())) / 100)),
        "quality_score": float(avg_quality),
        "cross_validation": cv_results,
        "feature_order": FEATURE_ORDER,
        "reference_sequence": best_sequence,
        "reference_sequence_frames": len(best_sequence)
    }

def init_empty_accuracy_csv(csv_path="output/training_accuracy_results.csv"):
    """Ensure the accuracy results CSV exists with proper headers."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    if not os.path.isfile(csv_path) or os.path.getsize(csv_path) == 0:
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()

def save_training_accuracy_csv(
    trained_model,
    csv_paths=None,
    fold_csv_paths=None,
    run_id=None,
    timestamp=None
):
    """
    Save training accuracy and cross-validation results to CSV files.
    Appends new rows so experiment history is preserved over time.
    """
    if csv_paths is None:
        csv_paths = [
            "output/training_accuracy_results.csv",
            "trained_model/training_accuracy_results.csv"
        ]
    elif isinstance(csv_paths, str):
        csv_paths = [csv_paths]
        
    if fold_csv_paths is None:
        fold_csv_paths = [
            "output/training_accuracy_folds.csv",
            "trained_model/training_accuracy_folds.csv"
        ]
    elif isinstance(fold_csv_paths, str):
        fold_csv_paths = [fold_csv_paths]

    now = datetime.datetime.now()
    if run_id is None:
        run_id = f"RUN-{now.strftime('%Y%m%d-%H%M%S')}"
    if timestamp is None:
        timestamp = now.isoformat(timespec="seconds")

    summary_rows = []
    fold_rows = []
    all_mean_accs = []
    all_samples = 0

    for technique, model in trained_model.items():
        cv = model.get("cross_validation")
        num_samples = model.get("num_samples", 0)
        all_samples += num_samples
        threshold = model.get("confidence_threshold", 0.5)
        quality = model.get("quality_score", 0.0)
        ref_frames = model.get("reference_sequence_frames", 0)
        
        if cv:
            mean_acc = cv.get("mean_accuracy", 0.0)
            std_acc = cv.get("std_accuracy", 0.0)
            min_acc = cv.get("min_accuracy", mean_acc)
            max_acc = cv.get("max_accuracy", mean_acc)
            folds = cv.get("folds", 0)
            status = "SUCCESS"
            all_mean_accs.append(mean_acc)
            
            fold_accs = cv.get("fold_accuracies", [])
            for idx, f_acc in enumerate(fold_accs, start=1):
                fold_rows.append({
                    "run_id": run_id,
                    "timestamp": timestamp,
                    "technique": technique,
                    "fold_index": idx,
                    "fold_accuracy": f"{f_acc:.4f}",
                    "fold_accuracy_pct": f"{f_acc * 100:.2f}%"
                })
        else:
            mean_acc = 0.0
            std_acc = 0.0
            min_acc = 0.0
            max_acc = 0.0
            folds = 0
            status = "INSUFFICIENT_SAMPLES"

        summary_rows.append({
            "run_id": run_id,
            "timestamp": timestamp,
            "technique": technique,
            "samples_count": num_samples,
            "cv_folds": folds,
            "mean_accuracy": f"{mean_acc:.4f}" if cv else "N/A",
            "mean_accuracy_pct": f"{mean_acc * 100:.2f}%" if cv else "N/A",
            "std_accuracy": f"{std_acc:.4f}" if cv else "N/A",
            "min_accuracy": f"{min_acc:.4f}" if cv else "N/A",
            "max_accuracy": f"{max_acc:.4f}" if cv else "N/A",
            "confidence_threshold": f"{threshold:.2f}",
            "quality_score": f"{quality:.4f}",
            "ref_sequence_frames": ref_frames,
            "status": status
        })

    # Add overall average row if multiple techniques were trained
    if len(all_mean_accs) > 1:
        overall_mean = float(np.mean(all_mean_accs))
        overall_std = float(np.std(all_mean_accs))
        summary_rows.append({
            "run_id": run_id,
            "timestamp": timestamp,
            "technique": "OVERALL_AVERAGE",
            "samples_count": all_samples,
            "cv_folds": "N/A",
            "mean_accuracy": f"{overall_mean:.4f}",
            "mean_accuracy_pct": f"{overall_mean * 100:.2f}%",
            "std_accuracy": f"{overall_std:.4f}",
            "min_accuracy": f"{min(all_mean_accs):.4f}",
            "max_accuracy": f"{max(all_mean_accs):.4f}",
            "confidence_threshold": "N/A",
            "quality_score": "N/A",
            "ref_sequence_frames": "N/A",
            "status": "SUCCESS"
        })

    # Write summary CSVs
    for path in csv_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        file_exists = os.path.isfile(path) and os.path.getsize(path) > 0
        with open(path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            if not file_exists:
                writer.writeheader()
            for row in summary_rows:
                writer.writerow(row)
        print(f"   💾 Saved accuracy results to: {path}")

    # Write fold-level CSVs
    if fold_rows:
        for path in fold_csv_paths:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            file_exists = os.path.isfile(path) and os.path.getsize(path) > 0
            with open(path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FOLD_CSV_HEADERS)
                if not file_exists:
                    writer.writeheader()
                for row in fold_rows:
                    writer.writerow(row)
            print(f"   💾 Saved fold details to: {path}")

    return summary_rows

def train_reference_model(reference_file="reference_data/reference_data.json"):
    """Train the reference model with validation and save accuracy CSV"""
    print("=" * 70)
    print("🧠 TRAINING REFERENCE MODEL - ENHANCED")
    print("=" * 70)
    
    # Load data
    data = load_reference_data(reference_file)
    if data is None:
        init_empty_accuracy_csv()
        return None
    
    print(f"📊 Loaded {len(data)} total samples")
    
    # Get unique techniques
    techniques = list(set(d["technique"] for d in data))
    print(f"📋 Techniques found: {techniques}")
    
    os.makedirs("trained_model", exist_ok=True)
    
    trained_model = {}
    
    for technique in techniques:
        print(f"\n🎯 Processing {technique}...")
        result = process_technique_data(data, technique)
        if result:
            trained_model[technique] = result
            print(f"   ✅ {result['num_samples']} samples processed")
            print(f"   📐 Joint angles: {list(result['joint_angles'].keys())}")
            print(f"   📊 Confidence threshold: {result['confidence_threshold']:.2f}")
            print(f"   ⭐ Quality score: {result['quality_score']*100:.1f}%")
    
    # Save trained model JSON
    with open("trained_model/reference_model.json", "w", encoding="utf-8") as f:
        json.dump(trained_model, f, indent=2)
    
    print("\n" + "=" * 70)
    print("✅ Training model JSON saved!")
    print(f"   Saved to: trained_model/reference_model.json")
    print("=" * 70)
    
    # Save training accuracy results CSV
    print("\n📊 Exporting accuracy results to CSV...")
    save_training_accuracy_csv(trained_model)
    
    # Print summary
    print("\n📊 TRAINING SUMMARY")
    print("-" * 60)
    for technique, model in trained_model.items():
        print(f"\n{technique}:")
        print(f"  Samples: {model['num_samples']}")
        print(f"  Confidence threshold: {model['confidence_threshold']:.2f}")
        print(f"  Quality score: {model['quality_score']*100:.1f}%")
        if model.get("cross_validation"):
            cv = model["cross_validation"]
            print(f"  Cross-validation: {cv['mean_accuracy']*100:.1f}% (±{cv['std_accuracy']*100:.1f}%)")
        print(f"  Angles: {', '.join(model['joint_angles'].keys())}")
        print(f"  Variance range: {min(model['std_angles'].values()):.2f} - {max(model['std_angles'].values()):.2f}")

    return trained_model

if __name__ == "__main__":
    train_reference_model()
