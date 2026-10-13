# CertiFlow — Bulk Certificate Generator API

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-green.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red.svg)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)

A production-grade, resilient backend REST API for bulk certificate generation. Built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, **Pydantic v2**, and **ReportLab**.

---

## 1. Project Overview

Organizations frequently need to generate certificates for large cohorts of participants following an event, workshop, or training course. Submitting certificates one-by-one introduces high network latency, while rendering hundreds of PDF documents in a synchronous HTTP request causes client timeouts, server worker exhaustion, and bad user experience.

**CertiFlow** solves this problem by:
- Accepting bulk requests containing course/event details and lists of recipients.
- Validating recipient data strictly before accepting the batch.
- Asynchronously dispatching certificate generation using background processing.
- Generating crisp, vector-based PDF certificates from a single professional template.
- Tracking real-time job progress (total, pending, completed, failed counts and percentage).
- Providing resilient per-recipient fault isolation: if one recipient certificate fails, the system continues processing all other valid recipients and records the exact failure reason.
- Providing direct PDF download endpoints.

---

## 2. Architecture

```
                                  +-------------------------------------------------------+
                                  |                     FastAPI API Layer                 |
                                  |                                                       |
[Client / Frontend] ------------> | 1. POST /api/v1/jobs (Validate Request Body)          |
                                  | 2. Persist GenerationJob & Certificate records        |
                                  | 3. Enqueue Background Task                            |
                                  | 4. Return 202 Accepted + job_id immediately           |
                                  +---------------------------+---------------------------+
                                                              |
                                                              | Async BackgroundTasks
                                                              v
                                  +-------------------------------------------------------+
                                  |               Background Worker Layer                 |
                                  |             (app/services/job_processor.py)           |
                                  |                                                       |
                                  | - Updates job status to 'PROCESSING'                  |
                                  | - Loops through recipients                            |
                                  | - For each recipient:                                 |
                                  |     +-- try:                                          |
                                  |     |     Generate PDF via ReportLab Engine           |
                                  |     |     Save to generated/{job_id}/{cert_id}.pdf    |
                                  |     |     Update status='GENERATED'                   |
                                  |     |     Increment success_count                     |
                                  |     +-- except:                                       |
                                  |           Catch & log error                           |
                                  |           Update status='FAILED' + error_message      |
                                  |           Increment failed_count                      |
                                  |     +-- commit progress live                          |
                                  | - Marks job 'COMPLETED' upon finish                   |
                                  +-------------------------------------------------------+
                                           |                                   |
                                           v                                   v
                             +---------------------------+       +---------------------------+
                             |    Relational Database    |       |        File System        |
                             |  PostgreSQL / SQLite      |       |  generated/{job_id}/*.pdf |
                             +---------------------------+       +---------------------------+
```

---

## 3. Technology Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (High-performance ASGI framework with Pydantic typing and OpenAPI docs).
- **Database:** [PostgreSQL 16](https://www.postgresql.org/) (Production-ready relational database with ACID compliance, relational integrity, foreign key cascades, and indexing). SQLite is supported out of the box for lightweight local testing.
- **ORM:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Modern typed ORM mappings, session pooling, and transaction control).
- **Data Validation:** [Pydantic v2](https://docs.pydantic.dev/) (Strict type enforcement, whitespace trimming, and email validation).
- **PDF Generation Engine:** [ReportLab](https://www.reportlab.com/) (Direct vector graphics and PDF canvas generation without headless browser overhead).
- **Database Migrations:** [Alembic](https://alembic.sqlalchemy.org/) (Version-controlled schema migrations).
- **Testing:** [Pytest](https://docs.pytest.org/) & `pytest-asyncio` (Automated unit and integration test suite).
- **Containerization:** [Docker & Docker Compose](https://www.docker.com/) (Multi-container orchestration with PostgreSQL health checks).

---

## 4. Project Structure

```
certiflow-bulk-certificate-api/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application factory, lifespan, CORS, and routes
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                 # Database session dependency injection
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── jobs.py             # Job creation, status progress, and certificate listing
│   │       └── certificates.py     # Certificate PDF streaming download endpoint
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic BaseSettings environment configuration
│   │   └── database.py             # SQLAlchemy engine & session factory
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                 # SQLAlchemy DeclarativeBase
│   │   ├── job.py                  # GenerationJob model
│   │   └── certificate.py          # Certificate model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── job.py                  # Request & response schemas for jobs
│   │   └── certificate.py          # Recipient and certificate response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── generator.py            # Predefined ReportLab PDF certificate template
│   │   └── job_processor.py        # Background execution service with fault isolation
│   └── utils/
│       ├── __init__.py
│       └── logger.py               # Standardized logging configuration
├── templates/                      # Assets / font directory
├── generated/                      # Target storage directory for generated PDF files
├── migrations/                     # Alembic schema migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
├── tests/                          # Automated Pytest suite
│   ├── __init__.py
│   ├── conftest.py                 # In-memory SQLite fixtures & TestClient configuration
│   ├── test_jobs.py                # Job lifecycle, listing, and filtering tests
│   ├── test_certificates.py        # Certificate download & edge case tests
│   ├── test_validation.py          # Input schema validation tests
│   └── test_generator.py           # ReportLab generation & fault tolerance tests
├── alembic.ini                     # Alembic migration configuration
├── requirements.txt                # Production Python dependencies
├── Dockerfile                      # Production Docker container build
├── docker-compose.yml              # Multi-container Compose config (API + PostgreSQL)
├── .env.example                    # Sample environment variables
├── .gitignore                      # Git ignore patterns
├── .dockerignore                  # Docker build ignore patterns
└── README.md                       # Comprehensive project documentation
```

---

## 5. Setup Instructions

### Prerequisites
- Python 3.10+ (tested with Python 3.11, 3.12, 3.13)
- Git
- Optional: Docker and Docker Compose (for containerized PostgreSQL)

### Option A: Local Setup (Quickstart with SQLite or local PostgreSQL)

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd certiflow-bulk-certificate-api
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # On Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   # Copy example env file
   cp .env.example .env
   ```
   *(By default, `.env.example` points to `sqlite:///./certiflow.db` for instant zero-dependency execution).*

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The interactive OpenAPI documentation will be available at:  
👉 **http://localhost:8000/docs**

---

### Option B: Docker Compose (Production Setup with PostgreSQL)

1. **Launch the entire stack with one command:**
   ```bash
   docker compose up --build -d
   ```

2. **Verify services are healthy:**
   ```bash
   docker compose ps
   ```

3. **View logs:**
   ```bash
   docker compose logs -f api
   ```

4. **Stop the stack:**
   ```bash
   docker compose down
   ```

---

### Option C: Vercel

This repository includes [`api/index.py`](./api/index.py) and [`vercel.json`](./vercel.json) so Vercel can discover and route the FastAPI ASGI application.

1. Import the repository into Vercel and keep the project root set to the repository root.
2. Deploy once. The `/`, `/health`, `/docs`, and `/api/v1/*` routes are handled by the FastAPI function.
3. For persistent data, add a hosted PostgreSQL connection string as the `DATABASE_URL` environment variable (Neon is a suitable option). Vercel's local filesystem and the fallback SQLite database under `/tmp` are temporary.
4. Add `STORAGE_DIR=/tmp/certiflow-generated` if generated PDFs are only needed during the request. For durable downloads, use object storage and replace the local file storage implementation.

Do not use the Docker Compose database hostname on Vercel; `db` is only resolvable inside the Compose network.

---

## 6. Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `APP_NAME` | `CertiFlow - Bulk Certificate Generator API` | Application title |
| `APP_VERSION` | `1.0.0` | API semantic version |
| `API_V1_STR` | `/api/v1` | Prefix for version 1 API endpoints |
| `DEBUG` | `false` | Enable SQL query echo and debug logs |
| `DATABASE_URL` | `sqlite:///./certiflow.db` | SQLAlchemy DB connection string |
| `STORAGE_DIR` | `generated` | Directory path where generated PDFs are stored |
| `TEMPLATES_DIR` | `templates` | Template directory for certificate assets |

For PostgreSQL:
```env
DATABASE_URL=postgresql://certiflow_user:certiflow_password@localhost:5432/certiflow_db
```

---

## 7. Database Setup & Migrations

The database schema utilizes two core tables: `generation_jobs` and `certificates`.

### Schema Structure
- **`generation_jobs`**:
  - `id` (VARCHAR(36), PK): UUID.
  - `title` (VARCHAR(255)): Certificate title.
  - `course_name` (VARCHAR(255)): Name of the program or event.
  - `issuer_name` (VARCHAR(255)): Organization or authority issuing the certificate.
  - `issue_date` (DATE): Issuance date displayed on certificate.
  - `status` (VARCHAR(50), indexed): `PENDING` | `PROCESSING` | `COMPLETED` | `FAILED`.
  - `total_count` (INTEGER): Total number of recipients.
  - `success_count` (INTEGER): Successfully generated count.
  - `failed_count` (INTEGER): Failed count.
  - `created_at` (DATETIME, UTC).
  - `started_at` (DATETIME, nullable).
  - `completed_at` (DATETIME, nullable).

- **`certificates`**:
  - `id` (VARCHAR(36), PK): UUID.
  - `job_id` (VARCHAR(36), FK -> `generation_jobs.id`, ON DELETE CASCADE, indexed).
  - `recipient_name` (VARCHAR(255)): Full recipient name.
  - `recipient_email` (VARCHAR(255), indexed): Recipient email address.
  - `status` (VARCHAR(50), indexed): `PENDING` | `GENERATED` | `FAILED`.
  - `file_path` (VARCHAR(500), nullable): Local storage path of generated PDF.
  - `error_message` (TEXT, nullable): Error message if rendering failed.
  - `created_at` (DATETIME, UTC).

### Running Migrations
To apply migrations:
```bash
alembic upgrade head
```

To create a new migration after model changes:
```bash
alembic revision --autogenerate -m "describe_change"
```

---

## 8. API & Frontend Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | **Interactive Frontend Web Dashboard** (jobs list, job inspector, live generator, PDF viewer) |
| `GET` | `/health` | Healthcheck endpoint |
| `POST` | `/api/v1/jobs` | Submit a bulk certificate generation job |
| `GET` | `/api/v1/jobs` | List all certificate generation jobs (ordered by date desc) |
| `GET` | `/api/v1/jobs/{job_id}` | Check job status, progress percentage, and counters |
| `GET` | `/api/v1/jobs/{job_id}/certificates` | List all certificates in a job (supports filtering & pagination) |
| `GET` | `/api/v1/certificates/{certificate_id}` | Retrieve / Download / Preview a generated certificate PDF |

### Interactive Web Dashboard Features:
- **Tabular Dataset Editor**: Edit recipient rows in an interactive table with Name, Email, and delete actions.
- **CSV Import**: 1-click import of `.csv` or `.txt` tabular callsets with automatic header detection.
- **Bi-directional Sync**: Instant toggle between Tabular Grid View and Raw CSV/Text paste mode.
- **Live Preview & Download**: Instant inline PDF viewing modal or direct file downloads.
- **Smart Polling**: Automatically monitors background tasks and pauses when all tasks are complete.

---

## 9. Example Usage & curl Commands

### Step 1: Create a Generation Job

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Certificate of Completion",
    "course_name": "Full Stack Backend Engineering",
    "issuer_name": "Tech Academy",
    "issue_date": "2026-10-07",
    "recipients": [
      {
        "recipient_name": "Alice Johnson",
        "recipient_email": "alice@example.com"
      },
      {
        "recipient_name": "Bob Smith",
        "recipient_email": "bob@example.com"
      }
    ]
  }'
```

**Response (`202 Accepted`):**
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "PENDING",
  "total_count": 2,
  "created_at": "2026-10-07T17:30:00.123456Z",
  "message": "Certificate generation job accepted and processing in background"
}
```

---

### Step 2: Check Job Status & Progress

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/3fa85f64-5717-4562-b3fc-2c963f66afa6"
```

**Response (`200 OK`):**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Certificate of Completion",
  "course_name": "Full Stack Backend Engineering",
  "issuer_name": "Tech Academy",
  "issue_date": "2026-10-07",
  "status": "COMPLETED",
  "total_count": 2,
  "success_count": 2,
  "failed_count": 0,
  "pending_count": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-07T17:30:00.123456Z",
  "started_at": "2026-10-07T17:30:00.189123Z",
  "completed_at": "2026-10-07T17:30:00.320456Z"
}
```

---

### Step 3: List Certificates for a Job

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/3fa85f64-5717-4562-b3fc-2c963f66afa6/certificates"
```

**Response (`200 OK`):**
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "total": 2,
  "items": [
    {
      "id": "c1f76d91-4e4b-4ec4-9bbf-5eb4232c2a01",
      "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "status": "GENERATED",
      "error_message": null,
      "created_at": "2026-10-07T17:30:00.123456Z",
      "download_url": "/api/v1/certificates/c1f76d91-4e4b-4ec4-9bbf-5eb4232c2a01"
    },
    {
      "id": "8b9e6f22-1b3c-4cf2-8356-d44203657e32",
      "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "recipient_name": "Bob Smith",
      "recipient_email": "bob@example.com",
      "status": "GENERATED",
      "error_message": null,
      "created_at": "2026-10-07T17:30:00.123456Z",
      "download_url": "/api/v1/certificates/8b9e6f22-1b3c-4cf2-8356-d44203657e32"
    }
  ]
}
```

---

### Step 4: Retrieve / Download Generated Certificate PDF

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/certificates/c1f76d91-4e4b-4ec4-9bbf-5eb4232c2a01" \
  --output "Certificate_Alice_Johnson.pdf"
```

Returns the binary PDF file stream with `Content-Type: application/pdf` and `Content-Disposition: attachment; filename="Certificate_Alice_Johnson.pdf"`.

---

## 10. Failure-Handling Approach

A central requirement of the assignment is fault isolation:
> *"A failure while generating one certificate should not unnecessarily prevent other valid certificates in the same job from being generated. The job status should provide enough information to identify successful and failed generations."*

### How CertiFlow Implements This:
1. **Request-Level Validation (Pydantic):**
   - Syntax validation (e.g. malformed email strings, missing recipient names, empty recipient lists) is caught upfront before a job is admitted, returning standard `422 Unprocessable Entity`.
2. **Recipient-Level Isolation:**
   - In `app/services/job_processor.py`, every recipient's PDF generation is enclosed in an isolated `try...except Exception` block.
   - If rendering fails for recipient #3 (e.g. invalid characters, memory constraint, or I/O fault):
     - The exception message is captured in `certificate.error_message`.
     - `certificate.status` is marked as `FAILED`.
     - `job.failed_count` is incremented.
     - The background worker logs the traceback and continues uninterrupted to recipient #4.
3. **Real-time Live Progress Commits:**
   - The database transaction commits after each recipient rather than doing one monolithic transaction at the end.
   - This ensures that if the server were abruptly terminated, progress is preserved and status endpoints reflect real-time processing counts.

---

## 11. Important Design Decisions (Interview Justifications)

During an interview, you may be asked to explain and justify key technical decisions. Here is the concise reasoning:

### Why FastAPI BackgroundTasks over Celery / Redis?
- **Decision:** Used FastAPI's native `BackgroundTasks`.
- **Justification:** For this assignment, introducing Redis/RabbitMQ and a distributed Celery worker introduces unnecessary operational complexity, extra infrastructure dependencies, and Docker compose overhead. FastAPI's built-in background task runner operates directly within the Python process, cleanly offloads PDF rendering from the HTTP request cycle, meets all concurrency needs, and avoids premature over-engineering.
- **How to Scale in Production:** If the workload expands to thousands of concurrent certificates across multiple nodes, the `process_generation_job` function is already isolated as a standalone callable, making it trivial to extract into a Celery/ARQ task or an SQS consumer without altering the core business logic or API contracts.

### Why ReportLab over Headless Browser (Puppeteer/Playwright/WeasyPrint)?
- **Decision:** Vector-based generation with ReportLab.
- **Justification:** Headless browsers require massive Docker base images, large RAM footprints per worker (often 200MB+ per Chromium process), and external OS packages. ReportLab is a pure Python C-accelerated library that produces compact vector PDFs (typically 2–10 KB) in under 50 milliseconds per page with zero external binaries.

### Why Separate `generation_jobs` and `certificates` Tables?
- **Decision:** Normalized relational structure with one-to-many relationship and foreign key cascade.
- **Justification:** Allows fast O(1) status queries on the job summary while enabling fine-grained inspection and individual downloads of each certificate. Cascade deletion ensures database hygiene if a job is purged.

---

## 12. Testing

The test suite covers every requirement from the assignment:
- Bulk generation job creation.
- Strict input validation (empty lists, invalid email formats, short names).
- ReportLab PDF generation and file structure validation.
- Real-time job status, pending count, and percentage calculation.
- Fault tolerance (simulated generation failure on one recipient while other recipients succeed).
- Certificate retrieval and file streaming.

### Running Tests:
Run the complete test suite with one command:
```bash
python -m pytest -v
```

**Expected Test Output:**
tests/test_certificates.py::test_download_generated_certificate_pdf PASSED
tests/test_certificates.py::test_download_nonexistent_certificate_returns_404 PASSED
tests/test_certificates.py::test_download_pending_or_failed_certificate_returns_400 PASSED
tests/test_generator.py::test_certificate_generator_creates_valid_pdf PASSED
tests/test_generator.py::test_individual_certificate_failure_fault_tolerance PASSED
tests/test_jobs.py::test_create_generation_job_success PASSED
tests/test_jobs.py::test_get_nonexistent_job_returns_404 PASSED
tests/test_jobs.py::test_list_job_certificates PASSED
tests/test_jobs.py::test_list_certificates_status_filter PASSED
tests/test_jobs.py::test_list_all_jobs PASSED
tests/test_jobs.py::test_frontend_dashboard_served PASSED
tests/test_validation.py::test_reject_empty_recipients_list PASSED
tests/test_validation.py::test_reject_invalid_recipient_email PASSED
tests/test_validation.py::test_reject_missing_required_fields PASSED
tests/test_validation.py::test_reject_short_recipient_name PASSED

============================= 15 passed in 0.84s ==============================
```
