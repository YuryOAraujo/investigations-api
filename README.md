# Investigation API

A modern, production-ready REST API for managing investigations built with **FastAPI**, **SQLAlchemy**, and **Keycloak** authentication.

## Features

- **FastAPI** - High-performance async Python web framework
- **PostgreSQL** - Robust relational database
- **Alembic** - Migrations and versioning
- **Keycloak** - Enterprise-grade authentication & authorization
- **JWT Tokens** - Secure token-based authentication
- **Role-Based Access Control (RBAC)** - Admin role bypasses all permission checks
- **MinIO** - S3-compatible object storage for PDF file attachments
- **File Upload** - Support for PDF attachments per investigation
- **Pagination** - Efficient data retrieval with skip/limit
- **Filtering** - Query by status, title, and more
- **Sorting** - Sort by any column (ascending/descending)
- **API Versioning** - `/api/v1/` ready for future versions
- **CORS** - Cross-Origin Resource Sharing enabled
- **Docker** - Containerized deployment

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Project Structure](#project-structure)
- [Development](#development)
- [Database](#database)

## Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 13+
- Docker & Docker Compose (optional)
- Keycloak instance
- MinIO (included in docker-compose)

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/investigations

# Keycloak
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=investigations
KEYCLOAK_CLIENT_ID=investigations-api

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=investigations
```

### Setup

```bash
# Clone repository
git clone https://github.com/YuryOAraujo/investigations-api.git
cd investigations-api

# Install dependencies
pip install -r requirements.txt

# Run with Docker Compose
docker-compose up -d
```

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export KEYCLOAK_URL=http://localhost:8080
export KEYCLOAK_REALM=investigations
export KEYCLOAK_CLIENT_ID=investigations-api
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/investigations

# Run the API
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API documentation.

### Docker Compose

```bash
docker-compose up -d
```

The API will be available at `http://localhost:8000`

**Service URLs:**
- API Documentation: `http://localhost:8000/docs`
- MinIO Console: `http://localhost:9001` (user: minioadmin, password: minioadmin)
- Keycloak: `http://localhost:8080`
- PostgreSQL: `localhost:5432`

## API Endpoints

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### List Investigations

```
GET /api/v1/investigations
```

**Query Parameters:**
- `skip` (int, default: 0) - Number of records to skip
- `limit` (int, default: 10, max: 100) - Max records to return
- `sort_by` (string, default: "created_at") - Field to sort by
- `sort_order` (string, default: "desc") - "asc" or "desc"
- `status` (string) - Filter by status: "open", "closed", "pending"
- `title` (string) - Filter by title (substring match)

**Example:**
```bash
GET /api/v1/investigations?skip=0&limit=10&sort_by=created_at&sort_order=desc&status=open
```

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "title": "Security Breach Investigation",
      "status": "open",
      "created_at": "2026-01-22T10:30:00+00:00"
    }
  ],
  "pagination": {
    "skip": 0,
    "limit": 10,
    "total": 1,
    "returned": 1
  }
}
```

### Get Investigation by ID

```
GET /api/v1/investigations/{investigation_id}
```

**Response:**
```json
{
  "id": 1,
  "title": "Security Breach Investigation",
  "status": "open",
  "pdf_file_path": "investigation_1/report.pdf",
  "created_at": "2026-01-22T10:30:00+00:00"
}
```

### Create Investigation

```
POST /api/v1/investigations
```

**Required Role:** `admin`

**Request Body:**
```json
{
  "title": "New Investigation",
  "status": "open"
}
```

**Response:** `201 Created`
```json
{
  "id": 2,
  "title": "New Investigation",
  "status": "open",
  "created_at": "2026-01-22T11:00:00+00:00"
}
```

### Update Investigation (Full)

```
PUT /api/v1/investigations/{investigation_id}
```

**Required Role:** `admin`

**Request Body:**
```json
{
  "title": "Updated Title",
  "status": "closed"
}
```

**Response:** `200 OK`

**Note:** PUT is idempotent - calling it multiple times produces the same result.

### Update Investigation (Partial)

```
PATCH /api/v1/investigations/{investigation_id}
```

**Required Role:** `admin`

**Request Body (only include fields to update):**
```json
{
  "status": "closed"
}
```

**Response:** `200 OK`

### Delete Investigation

```
DELETE /api/v1/investigations/{investigation_id}
```

**Required Role:** `admin`

**Response:** `204 No Content`

### Upload PDF to Investigation

```
POST /api/v1/investigations/{investigation_id}/upload-pdf
```

**Required Role:** `admin`

**Request:** Multipart form-data with PDF file

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/investigations/1/upload-pdf" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/report.pdf"
```

**Response:** `200 OK`
```json
{
  "message": "PDF uploaded successfully",
  "file_path": "investigation_1/report.pdf"
}
```

**Notes:**
- Only PDF files are allowed
- Maximum file size: 10MB
- Uploading a new PDF replaces the existing one

### Download Investigation PDF

```
GET /api/v1/investigations/{investigation_id}/pdf
```

**Required Role:** `investigator`

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/investigations/1/pdf" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output investigation_1.pdf
```

**Response:** `200 OK` - PDF file download

### Delete Investigation PDF

```
DELETE /api/v1/investigations/{investigation_id}/pdf
```

**Required Role:** `admin`

**Response:** `204 No Content`

**Note:** Deleting an investigation also deletes its associated PDF file automatically.

## Authentication

This API uses **Keycloak** for authentication with **JWT tokens**.

### Getting a Token

```bash
curl -X POST \
  http://keycloak:8080/realms/investigations/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'client_id=investigations-api&client_secret=YOUR_SECRET&grant_type=client_credentials'
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 300
}
```

### Using the Token

Include the token in the `Authorization` header:

```bash
curl -X GET \
  http://localhost:8000/api/v1/investigations \
  -H 'Authorization: Bearer eyJhbGc...'
```

### Roles

- **`admin`** - Full access to all endpoints (bypasses all role checks)
- **`investigator`** - Read-only access to investigations

**Admin Benefits:**
- Admins automatically bypass all role-based restrictions
- Can access any endpoint regardless of required roles
- Full CRUD operations on investigations

## Project Structure

```
investigations-api/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app initialization
│   ├── db.py                        # Database configuration
│   ├── models.py                    # SQLAlchemy ORM models
│   ├── schemas.py                   # Pydantic request/response schemas
│   ├── auth.py                      # Keycloak authentication
│   ├── dependencies.py              # Pagination & filtering
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── investigations.py    # Investigation endpoints
│   │       └── router.py            # V1 router setup
│   └── services/
│       ├── __init__.py
│       └── minio_service.py         # MinIO file operations
├── migrations/                      # Alembic migrations
│   ├── versions/
│   │   ├── 63ffc62e06da_initial_migration_create_investigations_.py
│   │   └── 80c8036b4761_add_pdf_file_path_to_investigations_.py
│   ├── env.py                       # Alembic environment configuration
│   ├── script.py.mako               # Migration template
│   └── README
├── alembic.ini                      # Alembic configuration
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Development

### Project Stack

| Component | Technology |
|-----------|-----------|
| Web Framework | FastAPI 0.100+ |
| Database | PostgreSQL 13+ |
| ORM | SQLAlchemy 2.0+ |
| Database Migrations | Alembic |
| Validation | Pydantic v2 |
| Authentication | Keycloak + JWT |
| Object Storage | MinIO |
| HTTP Client | httpx |
| Server | Uvicorn |

### Key Libraries

- **FastAPI** - Modern async web framework with automatic API docs
- **SQLAlchemy** - SQL toolkit and ORM
- **Pydantic** - Data validation and settings management
- **python-jose** - JWT token handling
- **httpx** - Async HTTP client for Keycloak JWKS fetching
- **Alembic** - Database migrations and versioning
- **MinIO** - S3-compatible object storage for file management
- **python-multipart** - Form data and file upload support

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

This project follows PEP 8 conventions. Format code with:

```bash
black app/
flake8 app/
```

## Database

### Schema

**investigations table:**
```sql
CREATE TABLE investigations (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    pdf_file_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Notes:**
- `pdf_file_path` stores the MinIO object path (e.g., "investigation_1/report.pdf")
- Files are stored in MinIO bucket named "investigations"

## Database Migrations

This project uses Alembic for database schema management. Migrations are automatically applied when the application starts.

### Common Commands

```bash
# View current migration status
docker-compose exec api alembic current

# View all migrations
docker-compose exec api alembic history --verbose

# Create a new migration
docker-compose exec api alembic revision --autogenerate -m "super detailed message here."

# Apply all pending migrations
docker-compose exec api alembic upgrade head

# Rollback last migration
docker-compose exec api alembic downgrade -1
```

## API Versioning

The API is versioned under `/api/v1/`. Future versions will use `/api/v2/`, `/api/v3/`, etc., allowing backward compatibility.

## License

This project is licensed under the MIT License.

Created for learning FastAPI patterns and best practices.

---

**Status Codes Used:**
- `200 OK` - Successful GET, PUT, PATCH
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing/invalid token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource doesn't exist
- `500 Internal Server Error` - Server error