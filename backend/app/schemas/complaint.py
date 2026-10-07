import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.models.complaint import ComplaintStatus
from app.schemas.category import CategoryRead
from app.schemas.user import UserRead


class ComplaintBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=150, description="Brief summary of the civic grievance")
    description: str = Field(..., min_length=10, max_length=5000, description="Detailed description of the issue")
    category_id: int = Field(..., description="ID of the municipal complaint category")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="GPS latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="GPS longitude coordinate")
    address: Optional[str] = Field(None, max_length=255, description="Physical street or location address")
    location_text: Optional[str] = Field(None, max_length=255, description="Physical street or location address alias")

    @field_validator("title", "description", mode="before")
    @classmethod
    def validate_non_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or only whitespace")
            return stripped
        return v

    @model_validator(mode="before")
    @classmethod
    def model_validate_location(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if values.get("location_text") and not values.get("address"):
                values["address"] = values["location_text"]
            elif values.get("address") and not values.get("location_text"):
                values["location_text"] = values["address"]
        return values


class ComplaintCreate(ComplaintBase):
    pass


class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus = Field(..., description="Target status transition")
    remarks: Optional[str] = Field(None, max_length=1000, description="Optional remarks or notes about the status change")

    @field_validator("remarks", mode="before")
    @classmethod
    def validate_remarks_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return v


class ComplaintAssign(BaseModel):
    officer_id: uuid.UUID = Field(..., description="UUID of the officer to assign")


class ComplaintAttachmentRead(BaseModel):
    id: uuid.UUID
    complaint_id: uuid.UUID
    original_filename: str
    stored_filename: str
    content_type: str
    file_size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplaintStatusHistoryRead(BaseModel):
    id: int
    complaint_id: uuid.UUID
    old_status: Optional[str]
    new_status: str
    changed_by_user_id: uuid.UUID
    remarks: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssignedOfficerRead(BaseModel):
    id: uuid.UUID
    badge_number: str
    designation: Optional[str] = None
    department_id: int
    user: Optional[UserRead] = None

    model_config = ConfigDict(from_attributes=True)


class ComplaintAIAnalysisRead(BaseModel):
    id: uuid.UUID
    complaint_id: uuid.UUID
    predicted_category: str
    category_confidence: float
    recommended_department_name: str
    recommended_department_code: str
    recommended_department_id: Optional[int] = None
    predicted_priority: str
    urgency_score: float
    is_low_confidence: bool
    model_version: str
    created_at: datetime

    @computed_field
    def category_prediction(self) -> Dict[str, Any]:
        return {
            "category": self.predicted_category,
            "confidence": self.category_confidence,
        }

    @computed_field
    def recommended_department(self) -> Dict[str, Any]:
        return {
            "name": self.recommended_department_name,
            "code": self.recommended_department_code,
            "confidence": self.category_confidence,
        }

    @computed_field
    def priority_prediction(self) -> Dict[str, Any]:
        return {
            "priority": self.predicted_priority,
            "urgency_score": self.urgency_score,
        }

    model_config = ConfigDict(from_attributes=True)


class ComplaintRead(BaseModel):
    id: uuid.UUID
    ticket_number: str
    citizen_id: uuid.UUID
    category_id: int
    category: Optional[CategoryRead] = None
    assigned_officer_id: Optional[uuid.UUID] = None
    title: str
    description: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    location_text: Optional[str] = None
    location: Optional[str] = None
    reference_priority: Optional[str] = None
    priority: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    citizen: Optional[UserRead] = None
    assigned_officer: Optional[AssignedOfficerRead] = None
    ai_analysis: Optional[ComplaintAIAnalysisRead] = None

    model_config = ConfigDict(from_attributes=True)


class ComplaintDetailRead(ComplaintRead):
    status_history: List[ComplaintStatusHistoryRead] = []
    attachments: List[ComplaintAttachmentRead] = []

    model_config = ConfigDict(from_attributes=True)


class ComplaintListResponse(BaseModel):
    items: List[ComplaintRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class OfficerStatsResponse(BaseModel):
    total: int
    submitted: int
    assigned: int
    in_progress: int
    resolved: int
    closed: int
    rejected: int
    avg_resolution_hours: Optional[float] = None
    resolution_rate: Optional[float] = None

