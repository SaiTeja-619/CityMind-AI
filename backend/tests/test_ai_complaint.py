import uuid
from unittest.mock import patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import ComplaintCategory
from app.models.complaint import Complaint
from app.models.complaint_ai_analysis import ComplaintAIAnalysis


@pytest.mark.asyncio
async def test_complaint_creation_generates_ai_analysis(
    client: AsyncClient,
    citizen_token: str,
    test_category: ComplaintCategory,
    db_session: AsyncSession,
):
    """Test that submitting a complaint automatically runs ML inference and persists AI analysis."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = {
        "title": "Major Drinking Water Pipeline Leak",
        "description": "The main clean drinking water line has ruptured and is flooding the colony street.",
        "category_id": test_category.id,
        "latitude": 28.6139,
        "longitude": 77.2090,
        "address": "Sector 4, Green Park",
    }

    response = await client.post("/api/v1/complaints", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()

    complaint_id = data["id"]
    assert "ai_analysis" in data
    assert data["ai_analysis"] is not None

    ai_data = data["ai_analysis"]
    assert ai_data["predicted_category"] == "WATER"
    assert 0.0 < ai_data["category_confidence"] <= 1.0
    assert ai_data["recommended_department_code"] == "WATER"
    assert ai_data["recommended_department_name"] == "Water"
    assert "predicted_priority" in ai_data
    assert "urgency_score" in ai_data
    assert ai_data["model_version"] == "tfidf-logreg-v1"

    # Verify nested convenience structures
    assert ai_data["category_prediction"]["category"] == "WATER"
    assert ai_data["recommended_department"]["code"] == "WATER"

    # Verify database persistence
    stmt = select(ComplaintAIAnalysis).where(ComplaintAIAnalysis.complaint_id == uuid.UUID(complaint_id))
    ai_record = (await db_session.execute(stmt)).scalar_one_or_none()
    assert ai_record is not None
    assert ai_record.predicted_category == "WATER"


@pytest.mark.asyncio
async def test_get_complaint_detail_includes_ai_analysis(
    client: AsyncClient,
    citizen_token: str,
    test_category: ComplaintCategory,
):
    """Test that fetching complaint details returns the persisted AI analysis."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = {
        "title": "Deep Pothole Crater on Tarmac",
        "description": "Severe road damage with fractured asphalt puncturing vehicle tires.",
        "category_id": test_category.id,
        "latitude": 28.6139,
        "longitude": 77.2090,
    }

    create_res = await client.post("/api/v1/complaints", json=payload, headers=headers)
    assert create_res.status_code == 201
    complaint_id = create_res.json()["id"]

    # Fetch complaint detail
    get_res = await client.get(f"/api/v1/complaints/{complaint_id}", headers=headers)
    assert get_res.status_code == 200
    detail = get_res.json()

    assert detail["ai_analysis"] is not None
    assert detail["ai_analysis"]["predicted_category"] == "ROADS"
    assert detail["ai_analysis"]["recommended_department_code"] == "ROADS"
    assert detail["ai_analysis"]["category_prediction"]["category"] == "ROADS"


@pytest.mark.asyncio
async def test_complaint_creation_resilient_to_ml_failure(
    client: AsyncClient,
    citizen_token: str,
    test_category: ComplaintCategory,
):
    """Verify that if ML inference fails/crashes, complaint creation still succeeds normally."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = {
        "title": "Streetlight Broken on Avenue",
        "description": "Lamps are out on 5th street.",
        "category_id": test_category.id,
        "latitude": 28.6139,
        "longitude": 77.2090,
    }

    # Simulate unexpected ML inference error
    with patch("app.services.complaint_service.analyze_complaint_text", side_effect=RuntimeError("ML Engine Crash")):
        response = await client.post("/api/v1/complaints", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "SUBMITTED"
        assert "id" in data
        # AI analysis gracefully remains None without crashing the request
        assert data.get("ai_analysis") is None
