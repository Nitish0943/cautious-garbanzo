from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RecipientCreate(BaseModel):
    recipient_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Full name of the certificate recipient",
        examples=["Alice Johnson"],
    )
    recipient_email: EmailStr = Field(
        ...,
        description="Valid email address of the recipient",
        examples=["alice.johnson@example.com"],
    )

    model_config = ConfigDict(str_strip_whitespace=True)


class CertificateResponse(BaseModel):
    id: str
    job_id: str
    recipient_name: str
    recipient_email: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    download_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CertificateListResponse(BaseModel):
    job_id: str
    total: int
    items: List[CertificateResponse]
