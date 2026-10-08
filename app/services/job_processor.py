from datetime import datetime, timezone
import traceback
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.job import GenerationJob
from app.models.certificate import Certificate
from app.services.generator import CertificateGenerator
from app.utils.logger import logger


def process_generation_job(job_id: str) -> None:
    """
    Background worker task to process certificate generation for a job.
    Fault-isolated per recipient: an error on one certificate does not halt the remaining ones.
    """
    db: Session = SessionLocal()
    generator = CertificateGenerator(output_dir=settings.STORAGE_DIR)

    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in background processor.")
            return

        # Transition to PROCESSING
        job.status = "PROCESSING"
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)

        logger.info(f"Started processing job {job_id} ({job.total_count} recipients)")

        for cert in job.certificates:
            # Skip if already generated (e.g. idempotency or retry)
            if cert.status == "GENERATED":
                continue

            try:
                # Attempt to generate the PDF
                file_path = generator.generate_pdf(
                    certificate_id=cert.id,
                    job_id=job.id,
                    recipient_name=cert.recipient_name,
                    title=job.title,
                    course_name=job.course_name,
                    issuer_name=job.issuer_name,
                    issue_date=job.issue_date,
                )

                cert.file_path = str(file_path)
                cert.status = "GENERATED"
                cert.error_message = None
                job.success_count += 1
                logger.info(f"Successfully generated certificate {cert.id} for {cert.recipient_name}")

            except Exception as exc:
                # Capture individual failure reason and continue processing remaining recipients
                error_trace = traceback.format_exc()
                logger.error(
                    f"Failed to generate certificate {cert.id} for recipient '{cert.recipient_name}': {exc}\n{error_trace}"
                )
                cert.status = "FAILED"
                cert.error_message = str(exc)
                job.failed_count += 1

            # Commit after each recipient so clients can monitor real-time progress
            db.commit()

        # Update final job state
        job.completed_at = datetime.now(timezone.utc)
        job.status = "COMPLETED"
        db.commit()
        logger.info(
            f"Finished job {job_id}: {job.success_count} succeeded, {job.failed_count} failed out of {job.total_count} total."
        )

    except Exception as exc:
        logger.critical(f"Fatal error processing job {job_id}: {exc}\n{traceback.format_exc()}")
        try:
            if job:
                job.status = "FAILED"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
