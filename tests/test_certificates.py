import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.certificate import Certificate
from app.models.job import GenerationJob


def test_download_generated_certificate_pdf(client: TestClient):
    payload = {
        "title": "Professional Certificate",
        "course_name": "Cloud Native Architecture",
        "issuer_name": "Cloud Native Institute",
        "recipients": [
            {"recipient_name": "Grace Hopper", "recipient_email": "grace@example.com"}
        ],
    }

    create_resp = client.post("/api/v1/jobs", json=payload)
    job_id = create_resp.json()["job_id"]

    # Get certificate ID
    list_resp = client.get(f"/api/v1/jobs/{job_id}/certificates")
    cert_id = list_resp.json()["items"][0]["id"]

    # Download PDF
    download_resp = client.get(f"/api/v1/certificates/{cert_id}")
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert download_resp.content.startswith(b"%PDF-")


def test_download_nonexistent_certificate_returns_404(client: TestClient):
    random_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/certificates/{random_id}")
    assert resp.status_code == 404


def test_download_pending_or_failed_certificate_returns_400(client: TestClient, db_session: Session):
    # Manually insert a pending and a failed certificate
    job = GenerationJob(
        id=str(uuid.uuid4()),
        title="Test Job",
        course_name="Test Course",
        issuer_name="Test Issuer",
        status="PROCESSING",
        total_count=2,
    )
    db_session.add(job)

    pending_cert = Certificate(
        id=str(uuid.uuid4()),
        job_id=job.id,
        recipient_name="Pending User",
        recipient_email="pending@example.com",
        status="PENDING",
    )
    failed_cert = Certificate(
        id=str(uuid.uuid4()),
        job_id=job.id,
        recipient_name="Failed User",
        recipient_email="failed@example.com",
        status="FAILED",
        error_message="Simulated rendering error",
    )
    db_session.add_all([pending_cert, failed_cert])
    db_session.commit()

    # Pending certificate download attempt
    resp_pending = client.get(f"/api/v1/certificates/{pending_cert.id}")
    assert resp_pending.status_code == 400
    assert "pending" in resp_pending.json()["detail"].lower()

    # Failed certificate download attempt
    resp_failed = client.get(f"/api/v1/certificates/{failed_cert.id}")
    assert resp_failed.status_code == 400
    assert "failed" in resp_failed.json()["detail"].lower()
    assert "Simulated rendering error" in resp_failed.json()["detail"]
