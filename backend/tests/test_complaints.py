import io
import re
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import ComplaintCategory
from app.models.officer import Officer
from app.models.user import User


# Helper payload for complaint creation
def make_complaint_payload(category_id: int, **overrides):
    payload = {
        "title": "Severe Pothole on Main Street",
        "description": "Deep asphalt crater creating vehicle hazard near traffic signal.",
        "category_id": category_id,
        "latitude": 28.6139,
        "longitude": 77.2090,
        "address": "Main Street, Sector 4",
    }
    payload.update(overrides)
    return payload


# ==============================================================================
# A. Complaint Creation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_create_complaint_success(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test authenticated citizen successfully creates a complaint."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = make_complaint_payload(test_category.id)

    response = await client.post("/api/v1/complaints", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["latitude"] == payload["latitude"]
    assert data["longitude"] == payload["longitude"]
    assert data["status"] == "SUBMITTED"
    assert data["category_id"] == test_category.id

    # Verify ticket number format: CM-YYYYMMDD-XXXX
    ticket = data["ticket_number"]
    assert re.match(r"^CM-\d{8}-[A-Z0-9]{4,}$", ticket)


@pytest.mark.asyncio
async def test_create_complaint_missing_title(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test validation rejection when title is missing."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = make_complaint_payload(test_category.id)
    del payload["title"]

    response = await client.post("/api/v1/complaints", json=payload, headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_complaint_blank_title(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test validation rejection when title is whitespace only."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = make_complaint_payload(test_category.id, title="     ")

    response = await client.post("/api/v1/complaints", json=payload, headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_complaint_missing_description(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test validation rejection when description is missing."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = make_complaint_payload(test_category.id)
    del payload["description"]

    response = await client.post("/api/v1/complaints", json=payload, headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_complaint_invalid_category(
    client: AsyncClient, citizen_token: str
):
    """Test rejection when category_id does not exist."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = make_complaint_payload(999999)

    response = await client.post("/api/v1/complaints", json=payload, headers=headers)
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_create_complaint_invalid_latitude(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test coordinate validation for latitude outside [-90, 90]."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = make_complaint_payload(test_category.id, latitude=110.5)

    response = await client.post("/api/v1/complaints", json=payload, headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_complaint_invalid_longitude(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test coordinate validation for longitude outside [-180, 180]."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = make_complaint_payload(test_category.id, longitude=-195.0)

    response = await client.post("/api/v1/complaints", json=payload, headers=headers)
    assert response.status_code == 422


# ==============================================================================
# B. Authorization & Access Control Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_create_complaint_unauthenticated(
    client: AsyncClient, test_category: ComplaintCategory
):
    """Test unauthenticated complaint creation returns 401."""
    payload = make_complaint_payload(test_category.id)
    response = await client.post("/api/v1/complaints", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_officer_cannot_create_complaint_as_citizen(
    client: AsyncClient, officer_token: str, test_category: ComplaintCategory
):
    """Test officer role cannot post directly to citizen-restricted POST /complaints."""
    headers = {"Authorization": f"Bearer {officer_token}"}
    payload = make_complaint_payload(test_category.id)
    response = await client.post("/api/v1/complaints", json=payload, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_citizen_views_own_complaint(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test citizen can access details of their own complaint."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    create_res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers,
    )
    complaint_id = create_res.json()["id"]

    get_res = await client.get(f"/api/v1/complaints/{complaint_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == complaint_id


@pytest.mark.asyncio
async def test_citizen_cannot_view_another_citizens_complaint(
    client: AsyncClient,
    citizen_token: str,
    another_citizen_token: str,
    test_category: ComplaintCategory,
):
    """Test citizen is forbidden from viewing another citizen's complaint."""
    # Citizen 1 creates complaint
    headers_1 = {"Authorization": f"Bearer {citizen_token}"}
    create_res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers_1,
    )
    complaint_id = create_res.json()["id"]

    # Citizen 2 attempts to view Citizen 1's complaint
    headers_2 = {"Authorization": f"Bearer {another_citizen_token}"}
    get_res = await client.get(f"/api/v1/complaints/{complaint_id}", headers=headers_2)
    assert get_res.status_code == 403
    assert "access denied" in get_res.json()["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_citizen_cannot_change_complaint_status(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test citizen is forbidden (403) from changing status."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    create_res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers,
    )
    complaint_id = create_res.json()["id"]

    patch_res = await client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status": "IN_PROGRESS", "remarks": "Trying to change"},
        headers=headers,
    )
    assert patch_res.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_view_any_complaint(
    client: AsyncClient,
    citizen_token: str,
    admin_token: str,
    test_category: ComplaintCategory,
):
    """Test admin has authorization to view any complaint."""
    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    create_res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers_citizen,
    )
    complaint_id = create_res.json()["id"]

    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    get_res = await client.get(f"/api/v1/complaints/{complaint_id}", headers=headers_admin)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == complaint_id


@pytest.mark.asyncio
async def test_officer_can_view_department_complaint(
    client: AsyncClient,
    citizen_token: str,
    officer_token: str,
    test_category: ComplaintCategory,
):
    """Test officer can view complaint whose category targets their department."""
    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    create_res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers_citizen,
    )
    complaint_id = create_res.json()["id"]

    headers_officer = {"Authorization": f"Bearer {officer_token}"}
    get_res = await client.get(f"/api/v1/complaints/{complaint_id}", headers=headers_officer)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == complaint_id


# ==============================================================================
# C. Status Workflow State Machine Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_status_workflow_progression(
    client: AsyncClient,
    citizen_token: str,
    officer_token: str,
    admin_token: str,
    test_category: ComplaintCategory,
):
    """
    Test full valid lifecycle:
    SUBMITTED -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> CLOSED
    """
    # 1. Citizen creates (status = SUBMITTED)
    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers_citizen,
    )
    complaint_id = res.json()["id"]
    assert res.json()["status"] == "SUBMITTED"

    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    # 2. SUBMITTED -> ASSIGNED
    res_assign = await client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status": "ASSIGNED", "remarks": "Assigned to Roads team"},
        headers=headers_admin,
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["status"] == "ASSIGNED"

    # 3. ASSIGNED -> IN_PROGRESS (Officer updates)
    headers_officer = {"Authorization": f"Bearer {officer_token}"}
    res_progress = await client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status": "IN_PROGRESS", "remarks": "Crew dispatched to site"},
        headers=headers_officer,
    )
    assert res_progress.status_code == 200
    assert res_progress.json()["status"] == "IN_PROGRESS"

    # 4. IN_PROGRESS -> RESOLVED
    res_resolve = await client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status": "RESOLVED", "remarks": "Pothole filled and sealed"},
        headers=headers_officer,
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "RESOLVED"
    assert res_resolve.json()["resolved_at"] is not None

    # 5. RESOLVED -> CLOSED
    res_close = await client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status": "CLOSED", "remarks": "Citizen confirmed satisfactory repair"},
        headers=headers_admin,
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"
    assert res_close.json()["closed_at"] is not None


@pytest.mark.asyncio
async def test_status_workflow_rejection(
    client: AsyncClient,
    citizen_token: str,
    admin_token: str,
    test_category: ComplaintCategory,
):
    """Test valid SUBMITTED -> REJECTED transition."""
    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers_citizen,
    )
    complaint_id = res.json()["id"]

    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    res_reject = await client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status": "REJECTED", "remarks": "Out of municipal jurisdiction"},
        headers=headers_admin,
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_invalid_status_transition_rejected_with_400(
    client: AsyncClient,
    citizen_token: str,
    admin_token: str,
    test_category: ComplaintCategory,
):
    """Test invalid status jump (e.g. SUBMITTED -> IN_PROGRESS) returns HTTP 400."""
    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers_citizen,
    )
    complaint_id = res.json()["id"]

    # Attempt illegal jump directly to IN_PROGRESS
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    bad_res = await client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status": "IN_PROGRESS", "remarks": "Illegal skip"},
        headers=headers_admin,
    )
    assert bad_res.status_code == 400
    data = bad_res.json()
    assert "invalid status transition" in data["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_cannot_transition_from_closed_status(
    client: AsyncClient,
    citizen_token: str,
    admin_token: str,
    test_category: ComplaintCategory,
):
    """Test CLOSED complaint cannot be reopened to SUBMITTED."""
    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers_citizen,
    )
    cid = res.json()["id"]

    # Transition to ASSIGNED -> IN_PROGRESS -> RESOLVED -> CLOSED
    await client.patch(f"/api/v1/complaints/{cid}/status", json={"status": "ASSIGNED"}, headers=headers_admin)
    await client.patch(f"/api/v1/complaints/{cid}/status", json={"status": "IN_PROGRESS"}, headers=headers_admin)
    await client.patch(f"/api/v1/complaints/{cid}/status", json={"status": "RESOLVED"}, headers=headers_admin)
    await client.patch(f"/api/v1/complaints/{cid}/status", json={"status": "CLOSED"}, headers=headers_admin)

    # Attempt to transition back to SUBMITTED
    reopen_res = await client.patch(
        f"/api/v1/complaints/{cid}/status",
        json={"status": "SUBMITTED"},
        headers=headers_admin,
    )
    assert reopen_res.status_code == 400


# ==============================================================================
# D. Status History Tracking Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_status_history_records_every_transition(
    client: AsyncClient,
    citizen_token: str,
    admin_token: str,
    test_category: ComplaintCategory,
):
    """Test initial history entry exists and every subsequent transition appends to history."""
    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers_citizen,
    )
    cid = res.json()["id"]

    # Initial history check
    detail = (await client.get(f"/api/v1/complaints/{cid}", headers=headers_citizen)).json()
    assert len(detail["status_history"]) == 1
    assert detail["status_history"][0]["new_status"] == "SUBMITTED"
    assert detail["status_history"][0]["old_status"] is None

    # Perform transition
    await client.patch(
        f"/api/v1/complaints/{cid}/status",
        json={"status": "ASSIGNED", "remarks": "Team assigned"},
        headers=headers_admin,
    )

    detail_after = (await client.get(f"/api/v1/complaints/{cid}", headers=headers_citizen)).json()
    assert len(detail_after["status_history"]) == 2
    assert detail_after["status_history"][1]["old_status"] == "SUBMITTED"
    assert detail_after["status_history"][1]["new_status"] == "ASSIGNED"
    assert detail_after["status_history"][1]["remarks"] == "Team assigned"


# ==============================================================================
# E. Ticket Generation & Citizen List Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_ticket_number_uniqueness(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test consecutive complaint submissions produce unique ticket numbers."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    res1 = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id, title="Issue One Here"),
        headers=headers,
    )
    res2 = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id, title="Issue Two Here"),
        headers=headers,
    )

    t1 = res1.json()["ticket_number"]
    t2 = res2.json()["ticket_number"]
    assert t1 != t2


@pytest.mark.asyncio
async def test_list_my_complaints_pagination(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test GET /api/v1/complaints/my returns only caller's complaints with pagination."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    res = await client.get("/api/v1/complaints/my?page=1&page_size=5", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "total_pages" in data


@pytest.mark.asyncio
async def test_list_my_complaints_with_assigned_officer_serialization(
    client: AsyncClient,
    citizen_token: str,
    admin_token: str,
    test_officer_user: User,
    test_category: ComplaintCategory,
):
    """
    Regression test:
    Verify GET /api/v1/complaints/my serializes complaints that have an assigned officer
    without raising MissingGreenlet on assigned_officer.user.
    """
    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    create_res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id, title="Pothole with Officer Assigned"),
        headers=headers_citizen,
    )
    assert create_res.status_code == 201
    cid = create_res.json()["id"]

    # Admin assigns the complaint to an officer
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    officer_profile_id = test_officer_user.officer_profile.id
    assign_res = await client.patch(
        f"/api/v1/complaints/{cid}/assign",
        json={"officer_id": str(officer_profile_id)},
        headers=headers_admin,
    )
    assert assign_res.status_code == 200

    # Citizen retrieves their complaints
    my_res = await client.get("/api/v1/complaints/my?page=1&page_size=10", headers=headers_citizen)
    assert my_res.status_code == 200
    data = my_res.json()
    assert data["total"] >= 1
    matched = [item for item in data["items"] if item["id"] == cid]
    assert len(matched) == 1
    complaint_item = matched[0]
    assert complaint_item["assigned_officer"] is not None
    assert complaint_item["assigned_officer"]["badge_number"] == test_officer_user.officer_profile.badge_number
    assert complaint_item["assigned_officer"]["user"] is not None
    assert complaint_item["assigned_officer"]["user"]["email"] == test_officer_user.email
    assert complaint_item["assigned_officer"]["user"]["full_name"] == test_officer_user.full_name



# ==============================================================================
# F. Attachment Security Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_upload_valid_jpeg_attachment(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test uploading a valid JPEG image file with magic bytes."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers,
    )
    cid = res.json()["id"]

    # JPEG magic bytes: \xff\xd8\xff...
    fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01" + b"\x00" * 100
    files = {"file": ("damage_photo.jpg", io.BytesIO(fake_jpeg), "image/jpeg")}

    att_res = await client.post(
        f"/api/v1/complaints/{cid}/attachments",
        files=files,
        headers=headers,
    )
    assert att_res.status_code == 201
    att_data = att_res.json()
    assert att_data["original_filename"] == "damage_photo.jpg"
    assert att_data["content_type"] == "image/jpeg"
    assert att_data["file_size"] == len(fake_jpeg)


@pytest.mark.asyncio
async def test_upload_valid_png_attachment(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test uploading a valid PNG image file with magic bytes."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers,
    )
    cid = res.json()["id"]

    # PNG magic bytes: \x89PNG\r\n\x1a\n...
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50
    files = {"file": ("evidence.png", io.BytesIO(fake_png), "image/png")}

    att_res = await client.post(
        f"/api/v1/complaints/{cid}/attachments",
        files=files,
        headers=headers,
    )
    assert att_res.status_code == 201
    assert att_res.json()["content_type"] == "image/png"


@pytest.mark.asyncio
async def test_upload_oversized_file_rejected(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test file larger than 5MB is rejected with 413 Payload Too Large."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers,
    )
    cid = res.json()["id"]

    # 5.5 MB payload
    oversized = b"\xff\xd8\xff" + b"\x00" * (6 * 1024 * 1024)
    files = {"file": ("huge_photo.jpg", io.BytesIO(oversized), "image/jpeg")}

    att_res = await client.post(
        f"/api/v1/complaints/{cid}/attachments",
        files=files,
        headers=headers,
    )
    assert att_res.status_code == 413


@pytest.mark.asyncio
async def test_upload_invalid_file_signature_rejected(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test spoofed file (e.g. plain text or executable labeled as image/jpeg) is rejected."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers,
    )
    cid = res.json()["id"]

    # Text content pretending to be JPEG
    spoofed = b"This is a malware script disguised as an image"
    files = {"file": ("exploit.jpg", io.BytesIO(spoofed), "image/jpeg")}

    att_res = await client.post(
        f"/api/v1/complaints/{cid}/attachments",
        files=files,
        headers=headers,
    )
    assert att_res.status_code == 400
    assert "magic bytes" in att_res.json()["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_upload_attachment_unauthorized_user_rejected(
    client: AsyncClient,
    citizen_token: str,
    another_citizen_token: str,
    test_category: ComplaintCategory,
):
    """Test another citizen cannot upload attachments to someone else's complaint."""
    headers_1 = {"Authorization": f"Bearer {citizen_token}"}
    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers_1,
    )
    cid = res.json()["id"]

    fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01" + b"\x00" * 20
    files = {"file": ("photo.jpg", io.BytesIO(fake_jpeg), "image/jpeg")}

    headers_2 = {"Authorization": f"Bearer {another_citizen_token}"}
    att_res = await client.post(
        f"/api/v1/complaints/{cid}/attachments",
        files=files,
        headers=headers_2,
    )
    assert att_res.status_code == 403


# ==============================================================================
# G. Officer Assignment Tests (ADMIN)
# ==============================================================================


@pytest.mark.asyncio
async def test_admin_assigns_officer_to_complaint(
    client: AsyncClient,
    citizen_token: str,
    admin_token: str,
    test_officer_user: User,
    test_category: ComplaintCategory,
):
    """Test admin assigns complaint to officer and status automatically transitions to ASSIGNED."""
    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers_citizen,
    )
    cid = res.json()["id"]

    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    officer_profile_id = test_officer_user.officer_profile.id

    assign_res = await client.patch(
        f"/api/v1/complaints/{cid}/assign",
        json={"officer_id": str(officer_profile_id)},
        headers=headers_admin,
    )
    assert assign_res.status_code == 200
    data = assign_res.json()
    assert data["status"] == "ASSIGNED"
    assert data["assigned_officer_id"] == str(officer_profile_id)


# ==============================================================================
# H. Additional Phase 2 Edge Case, Storage & Integrity Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_upload_valid_webp_attachment(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test uploading a valid WebP image file with proper magic bytes."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers,
    )
    cid = res.json()["id"]

    # WebP magic bytes: RIFF....WEBP
    fake_webp = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 30
    files = {"file": ("pothole.webp", io.BytesIO(fake_webp), "image/webp")}

    att_res = await client.post(
        f"/api/v1/complaints/{cid}/attachments",
        files=files,
        headers=headers,
    )
    assert att_res.status_code == 201
    assert att_res.json()["content_type"] == "image/webp"
    assert att_res.json()["original_filename"] == "pothole.webp"


@pytest.mark.asyncio
async def test_upload_unsafe_filename_rejected(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test path traversal or directory manipulation in upload filename is rejected with 400."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers,
    )
    cid = res.json()["id"]

    fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01" + b"\x00" * 20
    files = {"file": ("../../etc/passwd.jpg", io.BytesIO(fake_jpeg), "image/jpeg")}

    att_res = await client.post(
        f"/api/v1/complaints/{cid}/attachments",
        files=files,
        headers=headers,
    )
    assert att_res.status_code == 400
    assert "path traversal" in att_res.json()["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_officer_from_different_department_cannot_view_complaint(
    client: AsyncClient,
    citizen_token: str,
    db_session: AsyncSession,
    test_category: ComplaintCategory,
):
    """Test officer from Sanitation dept cannot view complaints assigned to Roads dept."""
    from app.core.security import create_access_token, get_password_hash
    from app.models.department import Department
    from app.models.officer import Officer
    from app.models.role import Role
    from sqlalchemy import select

    stmt = select(Department).where(Department.code == "SANITATION")
    sanitation_dept = (await db_session.execute(stmt)).scalar_one_or_none()
    if not sanitation_dept:
        sanitation_dept = Department(
            name="Sanitation",
            code="SANITATION",
            description="Sanitation department",
            contact_email="sanitation@test.gov",
            is_active=True,
        )
        db_session.add(sanitation_dept)
        await db_session.flush()

    role = (await db_session.execute(select(Role).where(Role.name == "OFFICER"))).scalar_one()
    sanitation_user = User(
        email="sanitation.officer@citymind.gov",
        hashed_password=get_password_hash("Password123!"),
        full_name="Sanitation Officer",
        role_id=role.id,
        is_active=True,
    )
    db_session.add(sanitation_user)
    await db_session.flush()

    sanitation_profile = Officer(
        user_id=sanitation_user.id,
        department_id=sanitation_dept.id,
        badge_number="TEST-SANITATION-001",
        designation="Inspector",
        is_available=True,
    )
    db_session.add(sanitation_profile)
    await db_session.commit()

    sanitation_token = create_access_token(subject=sanitation_user.id, role="OFFICER")

    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    create_res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers_citizen,
    )
    cid = create_res.json()["id"]

    headers_sanitation = {"Authorization": f"Bearer {sanitation_token}"}
    get_res = await client.get(f"/api/v1/complaints/{cid}", headers=headers_sanitation)
    assert get_res.status_code == 403
    assert "access denied" in get_res.json()["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_complaint_location_text_alias_and_fields(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test submitting with location_text alias and receiving computed location and reference priority."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = {
        "title": "Broken Streetlight on 4th Cross",
        "description": "Streetlight has been flickering and completely dark for 3 days.",
        "category_id": test_category.id,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "location_text": "4th Cross Road, Indiranagar",
    }

    res = await client.post("/api/v1/complaints", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["address"] == "4th Cross Road, Indiranagar"
    assert data["location_text"] == "4th Cross Road, Indiranagar"
    assert "Indiranagar" in data["location"]
    assert data["reference_priority"] == "HIGH"
    assert data["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_database_transaction_rollback_on_error(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory, monkeypatch
):
    """Test that a failure during complaint submission triggers rollback without committing."""
    from sqlalchemy.ext.asyncio import AsyncSession

    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = make_complaint_payload(test_category.id, title="Rollback Test Complaint")

    async def mock_failing_commit(self):
        raise RuntimeError("Simulated DB commit error")

    monkeypatch.setattr(AsyncSession, "commit", mock_failing_commit)

    with pytest.raises(RuntimeError):
        await client.post("/api/v1/complaints", json=payload, headers=headers)


@pytest.mark.asyncio
async def test_admin_assign_nonexistent_officer_rejected(
    client: AsyncClient,
    citizen_token: str,
    admin_token: str,
    test_category: ComplaintCategory,
):
    """Test assigning a non-existent officer ID returns 404 Not Found."""
    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    create_res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers_citizen,
    )
    cid = create_res.json()["id"]

    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    fake_officer_id = str(uuid.uuid4())
    assign_res = await client.patch(
        f"/api/v1/complaints/{cid}/assign",
        json={"officer_id": fake_officer_id},
        headers=headers_admin,
    )
    assert assign_res.status_code == 404
    assert "not found" in assign_res.json()["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_get_nonexistent_complaint_returns_404(
    client: AsyncClient, admin_token: str
):
    """Test fetching a non-existent complaint UUID returns 404."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = await client.get(f"/api/v1/complaints/{uuid.uuid4()}", headers=headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_max_attachment_count_limit_enforced(
    client: AsyncClient, citizen_token: str, test_category: ComplaintCategory
):
    """Test exceeding 5 attachments on a single complaint is rejected with 400."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    create_res = await client.post(
        "/api/v1/complaints",
        json=make_complaint_payload(test_category.id),
        headers=headers,
    )
    cid = create_res.json()["id"]

    fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01" + b"\x00" * 20

    # Upload 5 allowed attachments
    for i in range(5):
        files = {"file": (f"photo_{i}.jpg", io.BytesIO(fake_jpeg), "image/jpeg")}
        res = await client.post(f"/api/v1/complaints/{cid}/attachments", files=files, headers=headers)
        assert res.status_code == 201

    # 6th upload should be rejected
    files = {"file": ("photo_extra.jpg", io.BytesIO(fake_jpeg), "image/jpeg")}
    res_extra = await client.post(f"/api/v1/complaints/{cid}/attachments", files=files, headers=headers)
    assert res_extra.status_code == 400
    assert "maximum limit" in res_extra.json()["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_list_categories_endpoints(
    client: AsyncClient, test_category: ComplaintCategory
):
    """Test read-only category endpoints return active complaint categories."""
    # Test GET /api/v1/categories
    res1 = await client.get("/api/v1/categories")
    assert res1.status_code == 200
    data1 = res1.json()
    assert isinstance(data1, list)
    assert len(data1) >= 1
    assert any(c["id"] == test_category.id for c in data1)

    # Test GET /api/v1/complaints/categories
    res2 = await client.get("/api/v1/complaints/categories")
    assert res2.status_code == 200
    data2 = res2.json()
    assert isinstance(data2, list)
    assert len(data2) >= 1
    assert any(c["id"] == test_category.id for c in data2)



