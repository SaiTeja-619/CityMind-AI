import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.category import ComplaintCategory
    from app.models.complaint_ai_analysis import ComplaintAIAnalysis
    from app.models.complaint_attachment import ComplaintAttachment
    from app.models.complaint_status_history import ComplaintStatusHistory
    from app.models.officer import Officer
    from app.models.user import User


class ComplaintStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


ALLOWED_STATUS_TRANSITIONS: Dict[str, List[str]] = {
    ComplaintStatus.SUBMITTED.value: [
        ComplaintStatus.ASSIGNED.value,
        ComplaintStatus.REJECTED.value,
    ],
    ComplaintStatus.ASSIGNED.value: [
        ComplaintStatus.IN_PROGRESS.value,
        ComplaintStatus.REJECTED.value,
    ],
    ComplaintStatus.IN_PROGRESS.value: [
        ComplaintStatus.RESOLVED.value,
    ],
    ComplaintStatus.RESOLVED.value: [
        ComplaintStatus.CLOSED.value,
    ],
    ComplaintStatus.CLOSED.value: [],
    ComplaintStatus.REJECTED.value: [],
}


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ticket_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    citizen_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("complaint_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assigned_officer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("officers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(
        String(30),
        default=ComplaintStatus.SUBMITTED.value,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    citizen: Mapped["User"] = relationship("User", foreign_keys=[citizen_id], lazy="joined")
    category: Mapped["ComplaintCategory"] = relationship("ComplaintCategory", lazy="joined")
    assigned_officer: Mapped[Optional["Officer"]] = relationship(
        "Officer", foreign_keys=[assigned_officer_id], lazy="joined"
    )
    status_history: Mapped[List["ComplaintStatusHistory"]] = relationship(
        "ComplaintStatusHistory",
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="ComplaintStatusHistory.created_at.asc()",
    )
    attachments: Mapped[List["ComplaintAttachment"]] = relationship(
        "ComplaintAttachment",
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="ComplaintAttachment.created_at.asc()",
    )
    ai_analysis: Mapped[Optional["ComplaintAIAnalysis"]] = relationship(
        "ComplaintAIAnalysis",
        back_populates="complaint",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )

    # Response and frontend convenience properties
    @property
    def location_text(self) -> Optional[str]:
        return self.address

    @property
    def location(self) -> Optional[str]:
        return self.address or f"{self.latitude}, {self.longitude}"

    @property
    def reference_priority(self) -> Optional[str]:
        return self.category.default_priority if self.category else "MEDIUM"

    @property
    def priority(self) -> Optional[str]:
        return self.reference_priority

    def __repr__(self) -> str:
        return f"<Complaint id={self.id} ticket='{self.ticket_number}' status='{self.status}'>"
