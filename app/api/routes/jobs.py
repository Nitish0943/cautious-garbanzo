import io
import uuid
import zipfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Response, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.job import GenerationJob
from app.models.certificate import Certificate
from app.schemas.job import (
    JobCreateRequest,
    JobCreateResponse,
    JobStatusResponse,
    JobListResponse,
)
from app.schemas.certificate import (
    CertificateResponse,
    CertificateListResponse,
)
from app.services.job_processor import process_generation_job
from app.utils.logger import logger

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create bulk certificate generation job",
    description="Submits a list of recipients to generate certificates in the background.",
)
def create_generation_job(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # 1. Create Job record
    job_id = str(uuid.uuid4())
    job = GenerationJob(
        id=job_id,
        title=payload.title,
        course_name=payload.course_name,
        issuer_name=payload.issuer_name,
        issue_date=payload.issue_date,
        status="PENDING",
        total_count=len(payload.recipients),
        success_count=0,
        failed_count=0,
    )
    db.add(job)

    # 2. Create Certificate placeholder records for each recipient
    for recipient in payload.recipients:
        cert = Certificate(
            id=str(uuid.uuid4()),
            job_id=job_id,
            recipient_name=recipient.recipient_name,
            recipient_email=str(recipient.recipient_email),
            status="PENDING",
        )
        db.add(cert)

    db.commit()
    db.refresh(job)

    # 3. Queue background execution
    background_tasks.add_task(process_generation_job, job_id)
    logger.info(f"Queued generation job {job_id} with {job.total_count} recipients.")

    return JobCreateResponse(
        job_id=job.id,
        status=job.status,
        total_count=job.total_count,
        created_at=job.created_at,
        message="Certificate generation job accepted and processing in background",
    )


@router.get(
    "",
    response_model=JobListResponse,
    summary="List all certificate generation jobs",
    description="Returns all jobs ordered by creation date descending.",
)
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(GenerationJob).order_by(GenerationJob.created_at.desc())
    total = query.count()
    jobs = query.offset(skip).limit(limit).all()
    return JobListResponse(
        total=total,
        items=[
            JobStatusResponse(
                id=j.id,
                title=j.title,
                course_name=j.course_name,
                issuer_name=j.issuer_name,
                issue_date=j.issue_date,
                status=j.status,
                total_count=j.total_count,
                success_count=j.success_count,
                failed_count=j.failed_count,
                pending_count=j.pending_count,
                progress_percentage=j.progress_percentage,
                created_at=j.created_at,
                started_at=j.started_at,
                completed_at=j.completed_at,
            )
            for j in jobs
        ],
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get generation job status and progress",
    description="Check the current status, total recipients, success count, and failure count.",
)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation job '{job_id}' not found",
        )

    return JobStatusResponse(
        id=job.id,
        title=job.title,
        course_name=job.course_name,
        issuer_name=job.issuer_name,
        issue_date=job.issue_date,
        status=job.status,
        total_count=job.total_count,
        success_count=job.success_count,
        failed_count=job.failed_count,
        pending_count=job.pending_count,
        progress_percentage=job.progress_percentage,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get(
    "/{job_id}/certificates",
    response_model=CertificateListResponse,
    summary="List certificates for a job",
    description="Retrieve all recipient certificate records for a specific job with optional status filter.",
)
def list_job_certificates(
    job_id: str,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: PENDING, GENERATED, FAILED"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation job '{job_id}' not found",
        )

    query = db.query(Certificate).filter(Certificate.job_id == job_id)
    if status_filter:
        query = query.filter(Certificate.status == status_filter.upper())

    total = query.count()
    certs = query.offset(skip).limit(limit).all()

    items = []
    for c in certs:
        download_url = f"/api/v1/certificates/{c.id}" if c.status == "GENERATED" else None
        items.append(
            CertificateResponse(
                id=c.id,
                job_id=c.job_id,
                recipient_name=c.recipient_name,
                recipient_email=c.recipient_email,
                status=c.status,
                error_message=c.error_message,
                created_at=c.created_at,
                download_url=download_url,
            )
        )

    return CertificateListResponse(
        job_id=job_id,
        total=total,
        items=items,
    )


@router.get(
    "/{job_id}/download-all",
    summary="Download all generated certificates as a ZIP archive",
    description="Bundles all completed certificates for a job into a downloadable zip file.",
)
def download_all_certificates(job_id: str, db: Session = Depends(get_db)):
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation job '{job_id}' not found",
        )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for cert in job.certificates:
            if cert.status == "GENERATED" and cert.file_path and Path(cert.file_path).exists():
                safe_name = "".join(c for c in cert.recipient_name if c.isalnum() or c in (" ", "_", "-")).strip()
                arcname = f"Certificate_{safe_name.replace(' ', '_')}_{cert.id[:8]}.pdf"
                zf.write(cert.file_path, arcname=arcname)

    zip_buffer.seek(0)
    safe_course = "".join(c for c in job.course_name if c.isalnum() or c in (" ", "_", "-")).strip()
    filename = f"certificates_{safe_course.replace(' ', '_')}_{job_id[:8]}.zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

