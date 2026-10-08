import uuid
from fastapi.testclient import TestClient


def test_create_generation_job_success(client: TestClient):
    payload = {
        "title": "Certificate of Completion",
        "course_name": "Distributed Systems in Python",
        "issuer_name": "Engineering Council",
        "issue_date": "2026-10-07",
        "recipients": [
            {"recipient_name": "Alice Johnson", "recipient_email": "alice@example.com"},
            {"recipient_name": "Bob Smith", "recipient_email": "bob@example.com"},
            {"recipient_name": "Carol Danvers", "recipient_email": "carol@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202

    data = response.json()
    assert "job_id" in data
    assert data["total_count"] == 3
    assert data["status"] in ("PENDING", "COMPLETED")  # TestClient runs background tasks before returning

    job_id = data["job_id"]

    # Verify status endpoint
    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()

    assert status_data["id"] == job_id
    assert status_data["status"] == "COMPLETED"
    assert status_data["total_count"] == 3
    assert status_data["success_count"] == 3
    assert status_data["failed_count"] == 0
    assert status_data["pending_count"] == 0
    assert status_data["progress_percentage"] == 100.0
    assert status_data["started_at"] is not None
    assert status_data["completed_at"] is not None


def test_get_nonexistent_job_returns_404(client: TestClient):
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/jobs/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_job_certificates(client: TestClient):
    payload = {
        "title": "Certificate of Excellence",
        "course_name": "FastAPI Masterclass",
        "issuer_name": "Python Academy",
        "recipients": [
            {"recipient_name": "David Miller", "recipient_email": "david@example.com"},
            {"recipient_name": "Eva Green", "recipient_email": "eva@example.com"},
        ],
    }

    create_resp = client.post("/api/v1/jobs", json=payload)
    job_id = create_resp.json()["job_id"]

    list_resp = client.get(f"/api/v1/jobs/{job_id}/certificates")
    assert list_resp.status_code == 200
    data = list_resp.json()

    assert data["job_id"] == job_id
    assert data["total"] == 2
    assert len(data["items"]) == 2
    for item in data["items"]:
        assert item["status"] == "GENERATED"
        assert item["download_url"] is not None
        assert item["download_url"].startswith("/api/v1/certificates/")


def test_list_certificates_status_filter(client: TestClient):
    payload = {
        "course_name": "Filter Test Course",
        "issuer_name": "Academy",
        "recipients": [
            {"recipient_name": "Frank White", "recipient_email": "frank@example.com"}
        ],
    }

    create_resp = client.post("/api/v1/jobs", json=payload)
    job_id = create_resp.json()["job_id"]

    # Filter by GENERATED
    res_gen = client.get(f"/api/v1/jobs/{job_id}/certificates?status=GENERATED")
    assert res_gen.status_code == 200
    assert res_gen.json()["total"] == 1

    # Filter by FAILED (should be 0)
    res_failed = client.get(f"/api/v1/jobs/{job_id}/certificates?status=FAILED")
    assert res_failed.status_code == 200
    assert res_failed.json()["total"] == 0


def test_list_all_jobs(client: TestClient):
    payload_1 = {
        "course_name": "Course Alpha",
        "issuer_name": "Org Alpha",
        "recipients": [{"recipient_name": "Alpha User", "recipient_email": "alpha@example.com"}],
    }
    payload_2 = {
        "course_name": "Course Beta",
        "issuer_name": "Org Beta",
        "recipients": [{"recipient_name": "Beta User", "recipient_email": "beta@example.com"}],
    }
    client.post("/api/v1/jobs", json=payload_1)
    client.post("/api/v1/jobs", json=payload_2)

    resp = client.get("/api/v1/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2
    assert any(j["course_name"] == "Course Alpha" for j in data["items"])
    assert any(j["course_name"] == "Course Beta" for j in data["items"])


def test_frontend_dashboard_served(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "CertiFlow" in resp.text
    assert "<!DOCTYPE html>" in resp.text

