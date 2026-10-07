"""
Training script for CityMind AI Complaint Classification.
Trains a TF-IDF + Multinomial Logistic Regression pipeline on the development benchmark dataset.
Saves the serialized pipeline to ml/artifacts/category_classifier.joblib
and the genuine evaluation metrics to ml/artifacts/metrics.json.
"""
import os
import csv
import json
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

RANDOM_SEED = 42

def load_dataset(csv_path: str):
    texts = []
    labels = []
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("title") or "").strip()
            desc = (row.get("description") or "").strip()
            combined_text = f"{title} {desc}".strip()
            category = (row.get("category") or "").strip()
            if combined_text and category:
                texts.append(combined_text)
                labels.append(category)

    print(f"Loaded {len(texts)} samples across {len(set(labels))} classes from {csv_path}")
    return texts, labels

def train_and_evaluate():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_dir, "data", "municipal_complaints_dev.csv")
    artifacts_dir = os.path.join(base_dir, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    model_path = os.path.join(artifacts_dir, "category_classifier.joblib")
    metrics_path = os.path.join(artifacts_dir, "metrics.json")

    texts, labels = load_dataset(data_path)

    # Stratified 80/20 train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=0.20,
        random_state=RANDOM_SEED,
        stratify=labels,
    )

    print(f"Training split: {len(X_train)} samples, Test split: {len(X_test)} samples")

    # Define TF-IDF + Multinomial Logistic Regression Pipeline
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True,
            strip_accents="unicode",
            lowercase=True,
        )),
        ("clf", LogisticRegression(
            C=1.0,
            max_iter=1000,
            random_state=RANDOM_SEED,
            class_weight="balanced",
        )),
    ])

    print("Fitting model...")
    pipeline.fit(X_train, y_train)

    print("Evaluating model on test split...")
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)

    # Compute genuine metrics
    acc = float(accuracy_score(y_test, y_pred))
    macro_precision = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
    macro_recall = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

    classes = sorted(list(pipeline.classes_))
    report_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=classes).tolist()

    per_category = {}
    for c in classes:
        if c in report_dict:
            per_category[c] = {
                "precision": float(report_dict[c]["precision"]),
                "recall": float(report_dict[c]["recall"]),
                "f1_score": float(report_dict[c]["f1-score"]),
                "support": int(report_dict[c]["support"]),
            }

    metrics = {
        "model_name": "TF-IDF + Multinomial Logistic Regression",
        "model_version": "tfidf-logreg-v1",
        "random_seed": RANDOM_SEED,
        "dataset_size": len(texts),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "accuracy": round(acc, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "classes": classes,
        "per_category": per_category,
        "confusion_matrix": cm,
    }

    # Print summary
    print("=" * 60)
    print("GENUINE EVALUATION RESULTS")
    print("=" * 60)
    print(f"Accuracy:        {metrics['accuracy']:.4f}")
    print(f"Macro Precision: {metrics['macro_precision']:.4f}")
    print(f"Macro Recall:    {metrics['macro_recall']:.4f}")
    print(f"Macro F1:        {metrics['macro_f1']:.4f}")
    print("\nPer-Category Breakdown:")
    for c, stats in per_category.items():
        print(f"  {c:12s} - P: {stats['precision']:.3f}, R: {stats['recall']:.3f}, F1: {stats['f1_score']:.3f} (n={stats['support']})")
    print("=" * 60)

    # Save artifact and metrics
    joblib.dump(pipeline, model_path)
    print(f"Saved trained model artifact to: {model_path}")

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved metrics report to: {metrics_path}")

    return metrics

if __name__ == "__main__":
    train_and_evaluate()
