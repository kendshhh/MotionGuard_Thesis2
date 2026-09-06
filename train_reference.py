"""
TRAIN REFERENCE MODEL
Processes recorded data and creates optimized reference
"""

import json
import numpy as np
import os
from collections import defaultdict

def load_reference_data(filepath="reference_data/reference_data.json"):
    """Load recorded reference data"""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        print("   Run record_reference.py first!")
        return None

def process_technique_data(data, technique_name):
    """Process all samples for a technique"""
    samples = [d for d in data if d["technique"] == technique_name]
    
    if len(samples) == 0:
        return None
    
    # Average all joint angles
    avg_angles = defaultdict(list)
    for sample in samples:
        for key, value in sample["joint_angles"].items():
            avg_angles[key].append(value)
    
    final_angles = {}
    for key, values in avg_angles.items():
        final_angles[key] = np.mean(values)
    
    # Average all keypoints
    avg_keypoints = []
    for sample in samples:
        avg_keypoints.append(sample["keypoints"])
    final_keypoints = np.mean(avg_keypoints, axis=0).tolist()
    
    # Calculate variance for confidence
    variances = {}
    for key, values in avg_angles.items():
        variances[key] = np.var(values) if len(values) > 1 else 0.1
    
    return {
        "technique": technique_name,
        "joint_angles": final_angles,
        "keypoints": final_keypoints,
        "variance": variances,
        "num_samples": len(samples),
        "confidence_threshold": 0.5
    }

def train_reference_model():
    """Train the reference model from recorded data"""
    print("=" * 60)
    print("🧠 TRAINING REFERENCE MODEL")
    print("=" * 60)
    
    # Load data
    data = load_reference_data()
    if data is None:
        return
    
    print(f"📊 Loaded {len(data)} samples")
    
    # Get unique techniques
    techniques = list(set(d["technique"] for d in data))
    print(f"📋 Techniques: {techniques}")
    
    # Process each technique
    trained_model = {}
    for technique in techniques:
        print(f"\n🎯 Processing {technique}...")
        result = process_technique_data(data, technique)
        if result:
            trained_model[technique] = result
            print(f"   ✅ Samples: {result['num_samples']}")
            print(f"   📐 Angles: {list(result['joint_angles'].keys())}")
            print(f"   📊 Confidence threshold: {result['confidence_threshold']}")
    
    # Save trained model
    os.makedirs("trained_model", exist_ok=True)
    with open("trained_model/reference_model.json", "w") as f:
        json.dump(trained_model, f, indent=2)
    
    print("\n" + "=" * 60)
    print("✅ Training complete!")
    print(f"   Saved to: trained_model/reference_model.json")
    print("=" * 60)
    
    # Print summary
    print("\n📊 TRAINING SUMMARY")
    print("-" * 40)
    for technique, model in trained_model.items():
        print(f"{technique}:")
        print(f"  - {model['num_samples']} samples")
        print(f"  - Angles: {', '.join(model['joint_angles'].keys())}")
        print(f"  - Confidence threshold: {model['confidence_threshold']}")

if __name__ == "__main__":
    train_reference_model()