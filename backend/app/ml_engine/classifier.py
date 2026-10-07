"""
Machine Learning & Decision Support Engine for CityMind AI.
Provides:
1. Genuine ML text classification via serialized TF-IDF + Logistic Regression pipeline.
2. Probability estimation and low-confidence detection (< 0.45).
3. AI-assisted department recommendation based on predicted category.
4. Deterministic urgency and priority scoring based on category risk & hazard keywords.
"""
import os
import re
import logging
from typing import Any, Dict, Optional, Tuple
import joblib

logger = logging.getLogger(__name__)

# Model metadata
MODEL_VERSION = "tfidf-logreg-v1"
LOW_CONFIDENCE_THRESHOLD = 0.45

# Canonical Department Mappings (AI-assisted recommendation based on predicted category)
CATEGORY_DEPARTMENT_MAP: Dict[str, Dict[str, str]] = {
    "ROADS": {"code": "ROADS", "name": "Roads"},
    "WATER": {"code": "WATER", "name": "Water"},
    "WASTE": {"code": "WASTE", "name": "Waste Management"},
    "ELECTRICITY": {"code": "ELECTRICITY", "name": "Electricity"},
    "TRAFFIC": {"code": "TRAFFIC", "name": "Traffic"},
    "HEALTH": {"code": "HEALTH", "name": "Health"},
}

# Baseline Category Risk Weights for Urgency Decision-Support
CATEGORY_RISK_WEIGHTS: Dict[str, float] = {
    "TRAFFIC": 0.80,
    "HEALTH": 0.75,
    "WATER": 0.70,
    "ROADS": 0.70,
    "WASTE": 0.50,
    "ELECTRICITY": 0.45,
}

# Critical & High Hazard Indicators
CRITICAL_HAZARD_KEYWORDS = [
    "sparking", "fire", "live wire", "snapped wire", "burst", "fatal", "accident",
    "emergency", "exposed wire", "drowning", "flood", "collapse", "sinkhole",
    "gas leak", "poison", "deadly", "explosion", "ambulance", "head-on",
]

HIGH_HAZARD_KEYWORDS = [
    "overflow", "choked", "stagnant", "dengue", "malaria", "blackout",
    "contamination", "fumes", "toxic", "vomiting", "illness", "gridlock",
    "deep pothole", "crater", "severe", "hazardous",
]


class ComplaintClassifier:
    _instance: Optional["ComplaintClassifier"] = None
    _pipeline = None

    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            # Default location: ml/artifacts/category_classifier.joblib
            project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..")
            )
            model_path = os.path.join(project_root, "ml", "artifacts", "category_classifier.joblib")
        self.model_path = model_path
        self._load_model()

    @classmethod
    def get_instance(cls) -> "ComplaintClassifier":
        """Get or create singleton instance of ComplaintClassifier."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model(self) -> None:
        """Load joblib pipeline if not already loaded."""
        if self._pipeline is not None:
            return
        if not os.path.exists(self.model_path):
            logger.warning(
                f"ML model artifact not found at {self.model_path}. "
                "Inference will be unavailable until model is trained."
            )
            return
        try:
            self._pipeline = joblib.load(self.model_path)
            logger.info(f"Loaded ML model pipeline from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load ML model artifact from {self.model_path}: {e}")
            self._pipeline = None

    def is_available(self) -> bool:
        """Check if ML model pipeline is loaded and ready for inference."""
        if self._pipeline is None:
            self._load_model()
        return self._pipeline is not None

    def predict(self, title: str, description: str) -> Optional[Dict[str, Any]]:
        """
        Run genuine scikit-learn TF-IDF + Logistic Regression inference.
        Returns predicted category, probability estimate, low-confidence flag, and model version.
        """
        if not self.is_available():
            logger.warning("ML inference called but model pipeline is unavailable.")
            return None

        combined_text = f"{title or ''} {description or ''}".strip()
        if not combined_text:
            return None

        try:
            probabilities = self._pipeline.predict_proba([combined_text])[0]
            classes = self._pipeline.classes_

            top_idx = int(probabilities.argmax())
            predicted_category = str(classes[top_idx])
            confidence = float(probabilities[top_idx])

            is_low_confidence = confidence < LOW_CONFIDENCE_THRESHOLD

            return {
                "predicted_category": predicted_category,
                "confidence": confidence,
                "is_low_confidence": is_low_confidence,
                "model_version": MODEL_VERSION,
                "all_probabilities": {
                    str(c): float(p) for c, p in zip(classes, probabilities)
                },
            }
        except Exception as e:
            logger.error(f"Error during ML inference: {e}")
            return None


def calculate_urgency_and_priority(
    predicted_category: str,
    confidence: float,
    text: str,
) -> Tuple[str, float]:
    """
    Deterministic decision-support logic based on:
    - ML predicted category
    - Model probability estimate
    - Documented category risk
    - Hazard indicators
    
    Returns (priority_str, urgency_score_float).
    """
    base_risk = CATEGORY_RISK_WEIGHTS.get(predicted_category.upper(), 0.50)
    lower_text = text.lower()

    hazard_boost = 0.0
    for kw in CRITICAL_HAZARD_KEYWORDS:
        if kw in lower_text:
            hazard_boost += 0.30
            break

    for kw in HIGH_HAZARD_KEYWORDS:
        if kw in lower_text:
            hazard_boost += 0.15
            break

    # Urgency score between 0.0 and 1.0
    raw_score = (base_risk * confidence) + hazard_boost
    urgency_score = round(min(1.0, max(0.05, raw_score)), 3)

    if urgency_score >= 0.75:
        priority = "CRITICAL"
    elif urgency_score >= 0.55:
        priority = "HIGH"
    elif urgency_score >= 0.35:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    return priority, urgency_score


def analyze_complaint_text(
    title: str,
    description: str,
    department_id_map: Optional[Dict[str, int]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Full end-to-end AI analysis:
    1. Real ML category prediction & probability estimate.
    2. AI-assisted department recommendation.
    3. Deterministic priority and urgency calculation.
    """
    classifier = ComplaintClassifier.get_instance()
    ml_result = classifier.predict(title, description)
    if not ml_result:
        return None

    cat = ml_result["predicted_category"]
    conf = ml_result["confidence"]
    is_low_conf = ml_result["is_low_confidence"]
    version = ml_result["model_version"]

    # Department Recommendation
    dept_info = CATEGORY_DEPARTMENT_MAP.get(cat.upper(), {"code": cat.upper(), "name": cat.title()})
    dept_code = dept_info["code"]
    dept_name = dept_info["name"]
    dept_id = department_id_map.get(dept_code) if department_id_map else None

    # Priority & Urgency Calculation
    full_text = f"{title} {description}"
    priority, urgency_score = calculate_urgency_and_priority(cat, conf, full_text)

    return {
        "predicted_category": cat,
        "category_confidence": round(conf, 4),
        "is_low_confidence": is_low_conf,
        "recommended_department_name": dept_name,
        "recommended_department_code": dept_code,
        "recommended_department_id": dept_id,
        "predicted_priority": priority,
        "urgency_score": urgency_score,
        "model_version": version,
    }
