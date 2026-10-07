"""
End-to-End Live Verification of CityMind AI Decision Support Feature.
Verifies the complete flow:
Citizen submits grievance
       ↓
Real trained ML model analyzes title + description
       ↓
Predicted Category & Probability Estimate
       ↓
Department Recommendation
       ↓
Priority & Urgency Recommendation
       ↓
Database persistence of ComplaintAIAnalysis
       ↓
Citizen sees AI Decision Support in complaint details
       ↓
Admin sees AI Decision Support in complaint details
       ↓
Assigned Officer sees AI Decision Support in complaint details
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import ComplaintCategory
from app.models.complaint import Complaint
from app.models.complaint_ai_analysis import ComplaintAIAnalysis
from app.models.user import User


@pytest.mark.asyncio
async def test_end_to_end_ai_decision_support_flow(
    client: AsyncClient,
    test_citizen_user: User,
    citizen_token: str,
    test_admin_user: User,
    admin_token: str,
    test_officer_user: User,
    officer_token: str,
    test_category: ComplaintCategory,
    db_session: AsyncSession,
):
    c_headers = {"Authorization": f"Bearer {citizen_token}"}
    a_headers = {"Authorization": f"Bearer {admin_token}"}
    o_headers = {"Authorization": f"Bearer {officer_token}"}

    print("\n" + "=" * 70)
    print("STEP 1: Citizen Submits Civic Complaint with Real Grievance Text")
    print("=" * 70)

    complaint_payload = {
        "title": "Severe Pothole Crater on Main Arterial Road",
        "description": "Massive depression in the asphalt near the roundabout. Vehicles are violently bottoming out and two motorbikes have slipped on loose stones.",
        "category_id": test_category.id,
        "latitude": 28.6139,
        "longitude": 77.2090,
        "address": "Ring Road Junction, Sector 5",
    }

    create_res = await client.post("/api/v1/complaints", json=complaint_payload, headers=c_headers)
    assert create_res.status_code == 201, f"Failed: {create_res.status_code} {create_res.text}"
    comp_data = create_res.json()
    complaint_id = comp_data["id"]
    ticket_number = comp_data["ticket_number"]

    print(f"[+] Complaint Created: Ticket={ticket_number}, Status={comp_data['status']}")

    print("\n" + "=" * 70)
    print("STEP 2: Real Machine Learning Model Evaluates Grievance Text")
    print("=" * 70)

    ai = comp_data.get("ai_analysis")
    assert ai is not None, "AI Analysis was not generated!"

    print(f"[+] Real Model Prediction Results:")
    print(f"    - Model Name & Version:       {ai['model_version']}")
    print(f"    - Predicted Category:         {ai['predicted_category']}")
    print(f"    - Probability Estimate:       {ai['category_confidence']:.1%}")
    print(f"    - Low-Confidence Flag:        {ai['is_low_confidence']}")
    print(f"    - Recommended Department:     {ai['recommended_department_name']} ({ai['recommended_department_code']})")
    print(f"    - Decision-Support Priority:  {ai['predicted_priority']}")
    print(f"    - Calculated Urgency Score:   {ai['urgency_score']:.2f} / 1.00")

    assert ai["predicted_category"] == "ROADS"
    assert ai["recommended_department_code"] == "ROADS"
    assert ai["predicted_priority"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    print("\n" + "=" * 70)
    print("STEP 3: Verify Persistence in complaint_ai_analyses Database Table")
    print("=" * 70)

    stmt = select(ComplaintAIAnalysis).where(ComplaintAIAnalysis.complaint_id == uuid.UUID(complaint_id))
    persisted = (await db_session.execute(stmt)).scalar_one_or_none()
    assert persisted is not None
    assert persisted.predicted_category == "ROADS"
    assert persisted.recommended_department_code == "ROADS"
    print(f"[+] Verified 1:1 database row exists for complaint_id {complaint_id}")

    print("\n" + "=" * 70)
    print("STEP 4: Citizen Views Complaint Details with AI Analysis Card")
    print("=" * 70)

    cit_res = await client.get(f"/api/v1/complaints/{complaint_id}", headers=c_headers)
    assert cit_res.status_code == 200
    cit_data = cit_res.json()
    assert cit_data["ai_analysis"] is not None
    assert cit_data["ai_analysis"]["predicted_category"] == "ROADS"
    print("[+] Citizen successfully receives genuine AI Analysis in response payload.")

    print("\n" + "=" * 70)
    print("STEP 5: Admin Views Complaint and Uses AI Recommendation to Assign Officer")
    print("=" * 70)

    adm_res = await client.get(f"/api/v1/complaints/{complaint_id}", headers=a_headers)
    assert adm_res.status_code == 200
    adm_data = adm_res.json()
    assert adm_data["ai_analysis"] is not None
    print(f"[+] Admin viewed AI recommended department: {adm_data['ai_analysis']['recommended_department_name']}")

    # Admin assigns to officer
    officer_profile = test_officer_user.officer_profile
    assign_res = await client.patch(
        f"/api/v1/complaints/{complaint_id}/assign",
        json={"officer_id": str(officer_profile.id)},
        headers=a_headers,
    )
    assert assign_res.status_code == 200
    print(f"[+] Admin assigned complaint to Officer: {officer_profile.badge_number}")

    print("\n" + "=" * 70)
    print("STEP 6: Officer Views Assigned Complaint with AI Triage Data")
    print("=" * 70)

    off_res = await client.get(f"/api/v1/complaints/{complaint_id}", headers=o_headers)
    assert off_res.status_code == 200
    off_data = off_res.json()
    assert off_data["ai_analysis"] is not None
    assert off_data["ai_analysis"]["predicted_category"] == "ROADS"
    print("[+] Assigned Officer successfully views AI Decision Support and priority assessment.")

    print("\n" + "=" * 70)
    print("ALL 6 END-TO-END DEMONSTRATION STEPS VERIFIED AND PASSED!")
    print("=" * 70)
