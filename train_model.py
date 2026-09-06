"""
TRAIN REFERENCE MODEL - ENHANCED
With cross-validation and accuracy metrics
"""

import json
import numpy as np
import os
from collections import defaultdict
import random

FEATURE_ORDER = ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "hip"]

def ordered_angle_vector(angles):
    """Keep model vectors deterministic even when JSON key order differs."""
    return [float(angles.get(name, 0.0)) for name in FEATURE_ORDER]

def load_reference_data(filepath="reference_data/reference_data.json"):
    """Load recorded reference data"""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        print("   Run record_reference.py first!")
        return None

def cross_validate(data, technique_name, k_folds=3):
    """Perform k-fold cross-validation"""
    samples = [d for d in data if d["technique"] == technique_name]
    if len(samples) < k_folds:
        print(f"   ⚠️ Not enough samples for {k_folds}-fold validation")
        return None
    
    # Shuffle samples
    random.Random(42).shuffle(samples)
    fold_size = len(samples) // k_folds
    
    accuracies = []
    
    for fold in range(k_folds):
        # Split data
        test_start = fold * fold_size
        test_end = test_start + fold_size
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
        
        avg_score = np.mean(scores)
        accuracies.append(avg_score)
    
    if accuracies:
        return {
            "mean_accuracy": float(np.mean(accuracies)),
            "std_accuracy": float(np.std(accuracies)),
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

def train_reference_model():
    """Train the reference model with validation"""
    print("=" * 70)
    print("🧠 TRAINING REFERENCE MODEL - ENHANCED")
    print("=" * 70)
    
    # Load data
    data = load_reference_data()
    if data is None:
        return
    
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
    
    # Save trained model
    with open("trained_model/reference_model.json", "w") as f:
        json.dump(trained_model, f, indent=2)
    
    print("\n" + "=" * 70)
    print("✅ Training complete!")
    print(f"   Saved to: trained_model/reference_model.json")
    print("=" * 70)
    
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

if __name__ == "__main__":
    train_reference_model()
