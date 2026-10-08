import pytest
from fastapi.testclient import TestClient


def test_reject_empty_recipients_list(client: TestClient):
    payload = {
        "title": "Certificate of Completion",
        "course_name": "Full Stack Engineering",
        "issuer_name": "Tech Academy",
        "recipients": [],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_reject_invalid_recipient_email(client: TestClient):
    payload = {
        "title": "Certificate of Completion",
        "course_name": "Full Stack Engineering",
        "issuer_name": "Tech Academy",
        "recipients": [
            {"recipient_name": "Alice Johnson", "recipient_email": "invalid-email-address"}
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_reject_missing_required_fields(client: TestClient):
    # Missing course_name and issuer_name
    payload = {
        "recipients": [
            {"recipient_name": "Alice Johnson", "recipient_email": "alice@example.com"}
        ]
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_reject_short_recipient_name(client: TestClient):
    payload = {
        "course_name": "Full Stack Engineering",
        "issuer_name": "Tech Academy",
        "recipients": [
            {"recipient_name": "A", "recipient_email": "alice@example.com"}
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
