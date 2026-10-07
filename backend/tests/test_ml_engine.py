import pytest
from app.ml_engine.classifier import (
    ComplaintClassifier,
    analyze_complaint_text,
    calculate_urgency_and_priority,
    LOW_CONFIDENCE_THRESHOLD,
    MODEL_VERSION,
)


def test_classifier_loading():
    """Verify that ComplaintClassifier loads the trained pipeline artifact."""
    classifier = ComplaintClassifier.get_instance()
    assert classifier.is_available() is True
    assert classifier._pipeline is not None


def test_category_predictions():
    """Verify ML predictions across representative civic grievances for all 6 categories."""
    classifier = ComplaintClassifier.get_instance()

    test_cases = [
        ("Massive pothole on highway", "A large crater has formed on the tarmac puncturing vehicle tires.", "ROADS"),
        ("Drinking water pipeline burst", "Clean municipal water is gushing out of broken main line in street.", "WATER"),
        ("Dumpster overflowing with waste", "Trash bags and rotting kitchen garbage are scattered across the lane.", "WASTE"),
        ("Streetlight out and transformer dark", "Entire road is pitch dark at night because lamps are dead.", "ELECTRICITY"),
        ("Traffic signal stuck on red", "Vehicles backed up for two kilometers at busy intersection due to light fault.", "TRAFFIC"),
        ("Stagnant sewage in open drain", "Open nullah is choked with black sludge and breeding swarms of mosquitoes.", "HEALTH"),
    ]

    for title, desc, expected_cat in test_cases:
        res = classifier.predict(title, desc)
        assert res is not None, f"Failed prediction for {title}"
        assert res["predicted_category"] == expected_cat, f"Expected {expected_cat}, got {res['predicted_category']}"
        assert 0.0 < res["confidence"] <= 1.0
        assert res["model_version"] == MODEL_VERSION
        assert isinstance(res["all_probabilities"], dict)
        assert len(res["all_probabilities"]) == 6
        # Probabilities sum to approximately 1.0
        prob_sum = sum(res["all_probabilities"].values())
        assert abs(prob_sum - 1.0) < 0.01


def test_low_confidence_flag():
    """Verify that ambiguous/non-civic text triggers the is_low_confidence flag."""
    classifier = ComplaintClassifier.get_instance()
    # Ambiguous text lacking strong domain vocabulary
    res = classifier.predict("Random generic question", "Hello, I just wanted to ask an unrelated thing.")
    assert res is not None
    assert res["confidence"] < LOW_CONFIDENCE_THRESHOLD
    assert res["is_low_confidence"] is True


def test_department_recommendation():
    """Verify department recommendation maps predicted category to active department."""
    dept_id_map = {
        "ROADS": 1,
        "WATER": 2,
        "WASTE": 3,
        "ELECTRICITY": 4,
        "TRAFFIC": 5,
        "HEALTH": 6,
    }

    result = analyze_complaint_text(
        title="Drinking water contamination",
        description="Tap water is brown and smells like sewage",
        department_id_map=dept_id_map,
    )

    assert result is not None
    assert result["predicted_category"] == "WATER"
    assert result["recommended_department_code"] == "WATER"
    assert result["recommended_department_name"] == "Water"
    assert result["recommended_department_id"] == 2


def test_priority_urgency_calculation():
    """Verify that critical hazard triggers elevate urgency and priority."""
    # Grievance with critical hazard: 'live wire' + 'sparking'
    p_crit, u_crit = calculate_urgency_and_priority(
        "ELECTRICITY",
        0.80,
        "Live wire snapped on wet road and sparking continuously near pedestrians",
    )
    assert p_crit in ["CRITICAL", "HIGH"]
    assert u_crit >= 0.60

    # Low urgency routine issue
    p_low, u_low = calculate_urgency_and_priority(
        "ELECTRICITY",
        0.30,
        "Timer on street light turns off 10 minutes early in the morning",
    )
    assert p_low in ["MEDIUM", "LOW"]
    assert u_low < u_crit


def test_empty_input_handling():
    """Verify classifier handles empty or whitespace input gracefully."""
    classifier = ComplaintClassifier.get_instance()
    assert classifier.predict("", "") is None
    assert classifier.predict("   ", "   ") is None
