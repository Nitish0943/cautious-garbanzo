from datetime import date
from pathlib import Path
from unittest.mock import patch
from sqlalchemy.orm import Session
from app.services.generator import CertificateGenerator
from app.services.job_processor import process_generation_job
from app.models.job import GenerationJob
from app.models.certificate import Certificate


def test_certificate_generator_creates_valid_pdf(tmp_path: Path):
    generator = CertificateGenerator(output_dir=tmp_path)
    cert_id = "test-cert-123"
    job_id = "test-job-456"

    pdf_path = generator.generate_pdf(
        certificate_id=cert_id,
        job_id=job_id,
        recipient_name="Ada Lovelace",
        title="Certificate of Achievement",
        course_name="Computer Science Fundamentals",
        issuer_name="Pioneer Institute",
        issue_date=date(2026, 10, 7),
    )

    assert pdf_path.exists()
    assert pdf_path.is_file()
    assert pdf_path.stat().st_size > 1000  # ReportLab PDF with vectors is several KB

    with open(pdf_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"


def test_individual_certificate_failure_fault_tolerance(db_session: Session, tmp_path: Path):
    """
    Validates requirement:
    If one certificate fails, continue processing the remaining valid recipients.
    Clearly record successful and failed certificate generations.
    """
    job_id = "job-fault-tolerance-test"
    job = GenerationJob(
        id=job_id,
        title="Fault Tolerance Test Certificate",
        course_name="Resilience in Backend Design",
        issuer_name="Quality Assurance Org",
        status="PENDING",
        total_count=3,
        success_count=0,
        failed_count=0,
    )
    db_session.add(job)

    cert_good_1 = Certificate(
        id="cert-1",
        job_id=job_id,
        recipient_name="Good Recipient One",
        recipient_email="good1@example.com",
        status="PENDING",
    )
    cert_bad = Certificate(
        id="cert-2",
        job_id=job_id,
        recipient_name="Fail Recipient",
        recipient_email="fail@example.com",
        status="PENDING",
    )
    cert_good_2 = Certificate(
        id="cert-3",
        job_id=job_id,
        recipient_name="Good Recipient Two",
        recipient_email="good2@example.com",
        status="PENDING",
    )
    db_session.add_all([cert_good_1, cert_bad, cert_good_2])
    db_session.commit()

    # Original generate_pdf method
    real_generate_pdf = CertificateGenerator.generate_pdf

    def faulty_generate_pdf(self, *args, **kwargs):
        cert_id = kwargs.get("certificate_id") or (args[0] if len(args) > 0 else None)
        if cert_id == "cert-2":
            raise RuntimeError("Simulated rendering failure: corrupted font or memory limit")
        return real_generate_pdf(self, *args, **kwargs)

    with patch.object(CertificateGenerator, "generate_pdf", new=faulty_generate_pdf):
        process_generation_job(job_id)

    # Refresh records from database
    db_session.expire_all()
    updated_job = db_session.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    updated_cert_1 = db_session.query(Certificate).filter(Certificate.id == "cert-1").first()
    updated_cert_bad = db_session.query(Certificate).filter(Certificate.id == "cert-2").first()
    updated_cert_2 = db_session.query(Certificate).filter(Certificate.id == "cert-3").first()

    # Assertions
    assert updated_job.status == "COMPLETED"
    assert updated_job.total_count == 3
    assert updated_job.success_count == 2
    assert updated_job.failed_count == 1
    assert updated_job.pending_count == 0
    assert updated_job.progress_percentage == 100.0

    # Cert 1 (First good) succeeded
    assert updated_cert_1.status == "GENERATED"
    assert updated_cert_1.file_path is not None
    assert updated_cert_1.error_message is None

    # Cert 2 (Bad) failed gracefully with error recorded
    assert updated_cert_bad.status == "FAILED"
    assert updated_cert_bad.file_path is None
    assert "Simulated rendering failure" in updated_cert_bad.error_message

    # Cert 3 (Second good) processed and succeeded despite previous failure!
    assert updated_cert_2.status == "GENERATED"
    assert updated_cert_2.file_path is not None
    assert updated_cert_2.error_message is None
