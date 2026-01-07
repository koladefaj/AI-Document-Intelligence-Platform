# AI Document Intelligence Platform

[Live Demo: AI Document Intelligence API](https://document-intelligence-backend-production.up.railway.app/docs)


A high-performance, asynchronous document analysis system built with **FastAPI**, **Celery**, and **Ollama**. This platform allows users to upload **PDF (including scanned), DOCX, TXT, and XLSX** files, performs OCR when needed, and generates **AI-driven summaries** using local LLMs.


---

## 🚀 Features

- **User Management**: Secure authentication (JWT), user registration, password editing, and account deletion.
- **Intelligent Uploads**: Multi-format support (**PDF, DOCX, TXT, XLSX**) with **magic byte validation** to prevent spoofed files. Secure storage in **Cloudflare R2**. CORS enabled for web clients.
- **OCR Engine**: Automatic **Optical Character Recognition** for scanned PDFs, ensuring AI can read text from images.
- **Background Processing**: Celery-powered task queue to handle heavy AI workloads asynchronously.
- **Local AI Analysis**: Integration with **Ollama** (Qwen2.5/Llama3) for **private, secure document summarization**.
- **Scalable Infrastructure**: Designed for deployment on Railway with separate services for the API, Worker, and Database.

---
## 🔹 Tech Highlights

* **Pydantic**: Ensures type-safe request validation and response serialization.
* **Dependency Injection**: Promotes modular, testable, and maintainable code, especially for DB sessions, authentication, and services.
* **Security**: JWT Auth, magic-byte file validation, rate limiting, and CORS protection.

---

## 🏗️ Architecture

- **FastAPI**: Entry point for all requests and Swagger UI.
- **PostgreSQL**: Stores user metadata, document status, and AI analysis results.
- **Cloudflare R2**: S3-compatible object storage for physical file persistence.
- **Redis**: Message broker between the API and the Worker.
- **Celery Worker**: Performs OCR and communicates with the Ollama API.
- **Ollama**: Hosts the LLM (e.g., Qwen2.5:1.5b) on a dedicated internal service.

---

### 🚀 Deployment Overview
![Railway Microservices Setup](assets/railway-screenshot.png)
*Microservice architecture deployed on Railway showing API, Worker, Database, Redis, and AI services.*

---

## 🛠️ Setup & Installation

### Prerequisites

- Python 3.10+
- PostgreSQL & Redis
- Poetry
- An Ollama instance running (locally or on Railway)

### Environment Variables

Create a `.env` file in the root directory or copy `.env.example`:

```bash
# Application Environment
APP_ENV=production
USE_MINIO=false

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/dbname
DATABASE_SYNC_URL=postgresql://user:pass@host:port/dbname
DATABASE_USERNAME=user
DATABASE_PASSWORD=pass
DB_PORT=5432

# Redis
REDIS_URL=redis://host:port/0
REDIS_PORT=6379

# JWT
SECRET_KEY='your-secret-key'
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM="HS256"

# Gemini API
GEMINI_API="your-gemini-api-key"

# Storage
STORAGE_TYPE=r2
S3_BUCKET=document-bucket
S3_ENDPOINT=https://<accountid>.r2.cloudflarestorage.com
S3_ACCESS_KEY=<access-key>
S3_SECRET_KEY=<secret-key>

# MinIO (optional)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=document-bucket
MINIO_SECURE=False
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# AI Provider
AI_PROVIDER="ollama"
OLLAMA_MODEL="qwen2.5:1.5b"
```

---

### Installation Steps
1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/koladefaj/AI-Document-Intelligence-Platform.git
    cd AI-Document-Intelligence-Platform
    ```

2.  **Install Dependencies:**
    ```bash
    poetry install
    ```

3. **Run Database Migration**
    ```bash
    alembic upgrade head
    ```

4. **Start the API**
    ```bash
    poetry run uvicorn app.main:app --reload
    ```

7. **Start the Celery Worker**
    ```bash
    poetry run celery -A app.worker worker --loglevel=info
    ```
---
## 🧪 Testing & CI/CD

* **Automated Tests**: Project uses pytest for unit and integration tests.
Run tests locally with:
```bash
pytest
```
* **Continuous Integration**: GitHub Actions is configured to run tests automatically on every push and pull request. This ensures that your API and background tasks work correctly before deployment.

---

## API Reference
|Method|Endpoint|Description|
|------|--------|-----------|
|POST|/auth/register|Register a new user|
|POST|/auth/login|Login and get JWT tokens|
|POST|/auth/change-password|Update account password|
|DELETE|/auth/delete-account|Delete user account|
|POST|/documents/upload|Upload PDF/DOCX/TXT/XLSX for AI analysis|
|GET|/documents/{document_id}|Get status and AI summary result|
---


## Security
* **File Validation**: All uploads are scanned for magic bytes to prevent malicious file execution.
* **OCR Fallback**: Scanned documents are automatically routed through the OCR pipeline.
* **JWT Auth**: All document routes are protected and scoped to the document owner.
* **Rate Limiting**: Login and registration routes are limited to prevent brute-force attacks.
* **CORS Enabled**: Web clients can securely access the API.
---

## Supported Formats

* **PDF** (text or scanned)
* **DOCX**
* **TXT**
* **XLSX**
---

## 📚 Notes

* Scanned PDFs use **Tesseract OCR** to extract text for AI analysis.
* Large documents are truncated to 8,000 characters before sending to the AI to ensure performance.
* This project is designed for private, self-hosted AI summarization using local LLMs (Ollama).


    

