import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.complaint import Complaint
    from app.models.department import Department


class ComplaintAIAnalysis(Base):
    __tablename__ = "complaint_ai_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    complaint_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("complaints.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    predicted_category: Mapped[str] = mapped_column(String(50), nullable=False)
    category_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_department_name: Mapped[str] = mapped_column(String(100), nullable=False)
    recommended_department_code: Mapped[str] = mapped_column(String(50), nullable=False)
    recommended_department_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    predicted_priority: Mapped[str] = mapped_column(String(20), nullable=False)
    urgency_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_low_confidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="tfidf-logreg-v1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    complaint: Mapped["Complaint"] = relationship("Complaint", back_populates="ai_analysis")
    recommended_department: Mapped[Optional["Department"]] = relationship("Department", lazy="joined")

    def __repr__(self) -> str:
        return f"<ComplaintAIAnalysis id={self.id} complaint_id={self.complaint_id} category='{self.predicted_category}' confidence={self.category_confidence:.2f}>"
