from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.certificate import RecipientCreate


class JobCreateRequest(BaseModel):
    title: str = Field(
        default="Certificate of Completion",
        min_length=2,
        max_length=200,
        description="Certificate title",
        examples=["Certificate of Completion"],
    )
    course_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Name of the course, training, or event",
        examples=["Full Stack Backend Engineering"],
    )
    issuer_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Issuing organization or authority",
        examples=["Tech Academy Global"],
    )
    issue_date: Optional[date] = Field(
        default_factory=date.today,
        description="Date of issuance",
    )
    recipients: List[RecipientCreate] = Field(
        ...,
        min_length=1,
        description="List of recipients to generate certificates for",
    )

    model_config = ConfigDict(str_strip_whitespace=True)


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    total_count: int
    created_at: datetime
    message: str = "Certificate generation job accepted and processing in background"

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    id: str
    title: str
    course_name: str
    issuer_name: str
    issue_date: Optional[date] = None
    status: str
    total_count: int
    success_count: int
    failed_count: int
    pending_count: int
    progress_percentage: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    total: int
    items: List[JobStatusResponse]
