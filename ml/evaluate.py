"""
Standalone evaluation script for CityMind AI Complaint Classification.
Loads the serialized pipeline and evaluates against the benchmark dataset or custom text inputs.
"""
import os
import csv
import json
import joblib
from sklearn.metrics import classification_report, accuracy_score, f1_score

def evaluate():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, "artifacts", "category_classifier.joblib")
    data_path = os.path.join(base_dir, "data", "municipal_complaints_dev.csv")
    metrics_path = os.path.join(base_dir, "artifacts", "metrics.json")

    if not os.path.exists(model_path):
        print(f"Model artifact not found at {model_path}. Run ml/train.py first.")
        return

    pipeline = joblib.load(model_path)
    print(f"Loaded model artifact from {model_path}")

    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as f:
            saved_metrics = json.load(f)
        print("Stored Test Set Evaluation Metrics:")
        print(f"  Accuracy:        {saved_metrics.get('accuracy')}")
        print(f"  Macro Precision: {saved_metrics.get('macro_precision')}")
        print(f"  Macro Recall:    {saved_metrics.get('macro_recall')}")
        print(f"  Macro F1:        {saved_metrics.get('macro_f1')}")

    # Interactive sample tests
    sample_queries = [
        "Massive pothole crater on Main Ring Road puncturing tires",
        "Dirty brownish drinking water coming out of kitchen faucet",
        "Dumpster overflowing with rotting garbage bags on street",
        "Streetlight is completely dark and transformer is sparking",
        "Traffic signal stuck on red causing severe vehicle jam at junction",
        "Open sewage drain overflowing with black stagnant water and mosquito swarm",
        "Completely ambiguous general enquiry without civic keywords",
    ]

    print("\nDemonstration Predictions on Sample Inputs:")
    for text in sample_queries:
        probs = pipeline.predict_proba([text])[0]
        pred_idx = probs.argmax()
        pred_class = pipeline.classes_[pred_idx]
        conf = float(probs[pred_idx])
        is_low = conf < 0.45
        status = "LOW CONFIDENCE" if is_low else "CONFIDENT"
        print(f"Text: '{text}'")
        print(f"  -> Predicted: {pred_class} | Confidence: {conf:.1%} [{status}]\n")

if __name__ == "__main__":
    evaluate()
