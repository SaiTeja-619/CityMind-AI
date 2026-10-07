import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.ml_engine import analyze_complaint_text
from app.models.category import ComplaintCategory
from app.models.complaint import ALLOWED_STATUS_TRANSITIONS, Complaint, ComplaintStatus
from app.models.complaint_ai_analysis import ComplaintAIAnalysis
from app.models.complaint_attachment import ComplaintAttachment
from app.models.complaint_status_history import ComplaintStatusHistory
from app.models.department import Department
from app.models.officer import Officer
from app.models.user import User
from app.schemas.complaint import ComplaintCreate
from app.services.storage_service import MAX_ATTACHMENTS_PER_COMPLAINT, storage_service

logger = logging.getLogger(__name__)


class ComplaintService:
    @staticmethod
    async def generate_unique_ticket_number(db: AsyncSession) -> str:
        """Generate a unique human-readable ticket number in format CM-YYYYMMDD-XXXX."""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        for _ in range(15):
            # 4 alphanumeric characters (uppercase digits and letters)
            random_part = "".join(secrets.choice("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(4))
            candidate = f"CM-{date_str}-{random_part}"

            stmt = select(Complaint.id).where(Complaint.ticket_number == candidate)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if not existing:
                return candidate

        # Fallback if extremely dense
        return f"CM-{date_str}-{uuid.uuid4().hex[:6].upper()}"

    @classmethod
    async def create_complaint(
        cls,
        db: AsyncSession,
        citizen: User,
        complaint_in: ComplaintCreate,
    ) -> Complaint:
        """Create a new complaint and record the initial SUBMITTED status history in a single transaction."""
        # Validate category exists
        stmt = select(ComplaintCategory).where(
            ComplaintCategory.id == complaint_in.category_id,
            ComplaintCategory.is_active == True,  # noqa: E712
        )
        category = (await db.execute(stmt)).scalar_one_or_none()
        if not category:
            raise NotFoundError(f"Complaint category with ID {complaint_in.category_id} not found or inactive")

        ticket_number = await cls.generate_unique_ticket_number(db)

        complaint = Complaint(
            ticket_number=ticket_number,
            citizen_id=citizen.id,
            category_id=category.id,
            title=complaint_in.title,
            description=complaint_in.description,
            latitude=complaint_in.latitude,
            longitude=complaint_in.longitude,
            address=complaint_in.address,
            status=ComplaintStatus.SUBMITTED.value,
        )
        db.add(complaint)
        await db.flush()

        # Initial status history entry
        initial_history = ComplaintStatusHistory(
            complaint_id=complaint.id,
            old_status=None,
            new_status=ComplaintStatus.SUBMITTED.value,
            changed_by_user_id=citizen.id,
            remarks="Complaint submitted by citizen",
        )
        db.add(initial_history)

        # AI Analysis & Decision-Support (Fail-safe: failure must not block complaint creation)
        try:
            dept_stmt = select(Department.code, Department.id).where(Department.is_active == True)  # noqa: E712
            dept_rows = (await db.execute(dept_stmt)).all()
            dept_id_map = {str(row[0]).upper(): int(row[1]) for row in dept_rows}

            ai_data = analyze_complaint_text(
                title=complaint.title,
                description=complaint.description,
                department_id_map=dept_id_map,
            )
            if ai_data:
                ai_record = ComplaintAIAnalysis(
                    complaint_id=complaint.id,
                    predicted_category=ai_data["predicted_category"],
                    category_confidence=ai_data["category_confidence"],
                    recommended_department_name=ai_data["recommended_department_name"],
                    recommended_department_code=ai_data["recommended_department_code"],
                    recommended_department_id=ai_data.get("recommended_department_id"),
                    predicted_priority=ai_data["predicted_priority"],
                    urgency_score=ai_data["urgency_score"],
                    is_low_confidence=ai_data["is_low_confidence"],
                    model_version=ai_data["model_version"],
                )
                db.add(ai_record)
        except Exception as e:
            logger.warning(f"AI analysis could not be completed for complaint {complaint.id}: {e}")

        await db.commit()
        await db.refresh(complaint)

        # Reload with relationships
        return await cls.get_complaint_by_id(db, complaint.id)  # type: ignore

    @classmethod
    async def get_complaint_by_id(
        cls,
        db: AsyncSession,
        complaint_id: uuid.UUID,
    ) -> Optional[Complaint]:
        """Fetch complaint by UUID with all related models pre-loaded."""
        stmt = (
            select(Complaint)
            .options(
                selectinload(Complaint.citizen).selectinload(User.role),
                selectinload(Complaint.category),
                selectinload(Complaint.assigned_officer).selectinload(Officer.department),
                selectinload(Complaint.assigned_officer).selectinload(Officer.user).selectinload(User.role),
                selectinload(Complaint.status_history).selectinload(ComplaintStatusHistory.changed_by_user),
                selectinload(Complaint.attachments),
                selectinload(Complaint.ai_analysis).selectinload(ComplaintAIAnalysis.recommended_department),
            )
            .where(Complaint.id == complaint_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def list_citizen_complaints(
        cls,
        db: AsyncSession,
        citizen_id: uuid.UUID,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Complaint], int]:
        """List paginated complaints belonging strictly to the specified citizen."""
        offset = (page - 1) * page_size

        # Count total
        count_stmt = select(func.count(Complaint.id)).where(Complaint.citizen_id == citizen_id)
        total = (await db.execute(count_stmt)).scalar() or 0

        # Query items
        stmt = (
            select(Complaint)
            .options(
                selectinload(Complaint.category),
                selectinload(Complaint.assigned_officer).selectinload(Officer.user),
                selectinload(Complaint.assigned_officer).selectinload(Officer.department),
                selectinload(Complaint.citizen),
            )
            .where(Complaint.citizen_id == citizen_id)
            .order_by(Complaint.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list((await db.execute(stmt)).scalars().all())
        return items, total

    @classmethod
    async def list_officer_complaints(
        cls,
        db: AsyncSession,
        officer: Officer,
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        search: Optional[str] = None,
        assigned_only: bool = True,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Complaint], int]:
        """List complaints assigned to the officer or belonging to their department."""
        offset = (page - 1) * page_size

        if assigned_only:
            base_condition = (Complaint.assigned_officer_id == officer.id)
        else:
            base_condition = or_(
                Complaint.assigned_officer_id == officer.id,
                and_(
                    Complaint.assigned_officer_id.is_(None),
                    Complaint.category.has(ComplaintCategory.target_department_id == officer.department_id),
                ),
            )

        conditions = [base_condition]
        if status:
            conditions.append(Complaint.status == status.upper())
        if category_id:
            conditions.append(Complaint.category_id == category_id)
        if search and search.strip():
            pat = f"%{search.strip()}%"
            conditions.append(
                or_(
                    Complaint.ticket_number.ilike(pat),
                    Complaint.title.ilike(pat),
                    Complaint.description.ilike(pat),
                    Complaint.address.ilike(pat),
                )
            )

        count_stmt = select(func.count(Complaint.id)).where(*conditions)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Complaint)
            .options(
                selectinload(Complaint.category),
                selectinload(Complaint.assigned_officer).selectinload(Officer.user),
                selectinload(Complaint.assigned_officer).selectinload(Officer.department),
                selectinload(Complaint.citizen),
            )
            .where(*conditions)
            .order_by(Complaint.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list((await db.execute(stmt)).scalars().all())
        return items, total

    @classmethod
    async def list_all_complaints(
        cls,
        db: AsyncSession,
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        department_id: Optional[int] = None,
        assigned_officer_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Complaint], int]:
        """List all complaints with optional filtering and search (for ADMIN)."""
        offset = (page - 1) * page_size

        conditions = []
        if status:
            conditions.append(Complaint.status == status.upper())
        if category_id:
            conditions.append(Complaint.category_id == category_id)
        if department_id:
            conditions.append(
                or_(
                    Complaint.category.has(ComplaintCategory.target_department_id == department_id),
                    Complaint.assigned_officer.has(Officer.department_id == department_id),
                )
            )
        if assigned_officer_id:
            conditions.append(Complaint.assigned_officer_id == assigned_officer_id)
        if search and search.strip():
            pat = f"%{search.strip()}%"
            conditions.append(
                or_(
                    Complaint.ticket_number.ilike(pat),
                    Complaint.title.ilike(pat),
                    Complaint.description.ilike(pat),
                    Complaint.address.ilike(pat),
                )
            )

        count_stmt = select(func.count(Complaint.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Complaint)
            .options(
                selectinload(Complaint.category),
                selectinload(Complaint.assigned_officer).selectinload(Officer.user),
                selectinload(Complaint.assigned_officer).selectinload(Officer.department),
                selectinload(Complaint.citizen),
            )
        )
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(Complaint.created_at.desc()).offset(offset).limit(page_size)

        items = list((await db.execute(stmt)).scalars().all())
        return items, total

    @classmethod
    async def get_officer_stats(
        cls,
        db: AsyncSession,
        officer: Officer,
    ) -> Dict[str, Any]:
        """Calculate real complaint metrics strictly for complaints assigned to the officer."""
        status_stmt = (
            select(Complaint.status, func.count(Complaint.id))
            .where(Complaint.assigned_officer_id == officer.id)
            .group_by(Complaint.status)
        )
        status_rows = (await db.execute(status_stmt)).all()
        status_counts = {str(status_val): count for status_val, count in status_rows}

        submitted = status_counts.get(ComplaintStatus.SUBMITTED.value, 0)
        assigned = status_counts.get(ComplaintStatus.ASSIGNED.value, 0)
        in_progress = status_counts.get(ComplaintStatus.IN_PROGRESS.value, 0)
        resolved = status_counts.get(ComplaintStatus.RESOLVED.value, 0)
        closed = status_counts.get(ComplaintStatus.CLOSED.value, 0)
        rejected = status_counts.get(ComplaintStatus.REJECTED.value, 0)
        total = sum(status_counts.values())

        # Average resolution time calculation
        # Uses created_at and resolved_at for resolved or closed complaints
        res_stmt = select(Complaint.created_at, Complaint.resolved_at).where(
            Complaint.assigned_officer_id == officer.id,
            Complaint.resolved_at.is_not(None),
        )
        res_rows = (await db.execute(res_stmt)).all()

        avg_resolution_hours = None
        if res_rows:
            durations = [
                (r[1] - r[0]).total_seconds() / 3600.0
                for r in res_rows
                if r[0] is not None and r[1] is not None and (r[1] >= r[0])
            ]
            if durations:
                avg_resolution_hours = round(sum(durations) / len(durations), 1)

        resolution_rate = None
        if total > 0:
            resolution_rate = round(((resolved + closed) / total) * 100.0, 1)

        return {
            "total": total,
            "submitted": submitted,
            "assigned": assigned,
            "in_progress": in_progress,
            "resolved": resolved,
            "closed": closed,
            "rejected": rejected,
            "avg_resolution_hours": avg_resolution_hours,
            "resolution_rate": resolution_rate,
        }

    @classmethod
    async def update_complaint_status(
        cls,
        db: AsyncSession,
        complaint: Complaint,
        new_status: str,
        user: User,
        remarks: Optional[str] = None,
    ) -> Complaint:
        """Validate and transition complaint status, updating timestamps and recording history atomically."""
        old_status = complaint.status
        allowed = ALLOWED_STATUS_TRANSITIONS.get(old_status, [])

        if new_status not in allowed:
            raise BadRequestError(
                f"Invalid status transition from '{old_status}' to '{new_status}'. Allowed transitions: {allowed}"
            )

        now = datetime.now(timezone.utc)
        complaint.status = new_status
        complaint.updated_at = now

        if new_status == ComplaintStatus.RESOLVED.value:
            complaint.resolved_at = now
        elif new_status == ComplaintStatus.CLOSED.value:
            complaint.closed_at = now

        # Add history record
        history = ComplaintStatusHistory(
            complaint_id=complaint.id,
            old_status=old_status,
            new_status=new_status,
            changed_by_user_id=user.id,
            remarks=remarks,
            created_at=now,
        )
        db.add(history)

        await db.commit()
        await db.refresh(complaint)

        return await cls.get_complaint_by_id(db, complaint.id)  # type: ignore

    @classmethod
    async def assign_complaint(
        cls,
        db: AsyncSession,
        complaint: Complaint,
        officer_id: uuid.UUID,
        admin_user: User,
    ) -> Complaint:
        """Assign an officer to the complaint. If in SUBMITTED, transitions to ASSIGNED."""
        # Verify officer exists
        stmt = select(Officer).options(selectinload(Officer.user)).where(Officer.id == officer_id)
        officer = (await db.execute(stmt)).scalar_one_or_none()
        if not officer:
            raise NotFoundError(f"Officer with ID {officer_id} not found")

        old_status = complaint.status
        complaint.assigned_officer_id = officer.id
        now = datetime.now(timezone.utc)
        complaint.updated_at = now

        # If currently SUBMITTED, perform transition to ASSIGNED
        if old_status == ComplaintStatus.SUBMITTED.value:
            complaint.status = ComplaintStatus.ASSIGNED.value
            history = ComplaintStatusHistory(
                complaint_id=complaint.id,
                old_status=old_status,
                new_status=ComplaintStatus.ASSIGNED.value,
                changed_by_user_id=admin_user.id,
                remarks=f"Assigned to Officer {officer.badge_number} ({officer.user.full_name})",
                created_at=now,
            )
            db.add(history)
        else:
            # Reassignment within current status
            history = ComplaintStatusHistory(
                complaint_id=complaint.id,
                old_status=old_status,
                new_status=old_status,
                changed_by_user_id=admin_user.id,
                remarks=f"Reassigned to Officer {officer.badge_number} ({officer.user.full_name})",
                created_at=now,
            )
            db.add(history)

        await db.commit()
        await db.refresh(complaint)
        return await cls.get_complaint_by_id(db, complaint.id)  # type: ignore

    @classmethod
    async def add_attachment(
        cls,
        db: AsyncSession,
        complaint: Complaint,
        user: User,
        content: bytes,
        original_filename: str,
        content_type: str,
    ) -> ComplaintAttachment:
        """Validate and store attachment file, recording metadata in database."""
        # Check current attachment count
        count_stmt = select(func.count(ComplaintAttachment.id)).where(
            ComplaintAttachment.complaint_id == complaint.id
        )
        current_count = (await db.execute(count_stmt)).scalar() or 0
        if current_count >= MAX_ATTACHMENTS_PER_COMPLAINT:
            raise BadRequestError(
                f"Maximum limit of {MAX_ATTACHMENTS_PER_COMPLAINT} attachments reached for this complaint"
            )

        # Save to disk / storage
        stored_filename, storage_path = await storage_service.save_file(
            content=content,
            complaint_id=complaint.id,
            content_type=content_type,
            original_filename=original_filename,
        )

        attachment = ComplaintAttachment(
            complaint_id=complaint.id,
            uploaded_by_user_id=user.id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            file_size=len(content),
            storage_path=storage_path,
        )
        db.add(attachment)
        await db.commit()
        await db.refresh(attachment)
        return attachment
