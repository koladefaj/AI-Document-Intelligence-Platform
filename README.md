# AI Document Intelligence & RAG Platform

[Live Demo: Swagger UI](http://localhost:8000/docs) (Local Only)

A high-performance, asynchronous Document Intelligence and **Retrieval-Augmented Generation (RAG)** platform. Built with **FastAPI**, **Celery**, and **Ollama**, this system allows users to transform static documents into interactive, searchable AI assets.

---

## 🚀 Key Features

- **Advanced RAG Engine**: Perform semantic search and contextual Q&A across your entire document library.
- **ORM-Native Vector Store**: High-performance vector storage in PostgreSQL using `pgvector` with `HNSW` indexing for sub-second similarity retrieval.
- **Architecture Decoupling**: Built using **Dependency Injection** (DI) and interface patterns, allowing for hot-swapping storage providers (Local, MinIO, R2) and AI models.
- **Intelligent Deduplication**: Uses **SHA-256 content hashing** to instantly identify duplicate files, skipping expensive AI processing and cloning results.
- **Hardware Acceleration**: Native support for **NVIDIA GPU Offloading** (RTX 4060+) when using local Ollama.
- **OCR Engine**: Automatic Tesseract-powered OCR for scanned PDFs and images.
- **Usage Tracking**: Per-user token consumption monitoring and quota management.

---

## 🛡️ Resilience & Task Reliability

The platform is designed for **Zero Data Loss** and high availability in the background processing pipeline:

- **Late Acknowledgement**: Workers use `task_acks_late=True`, ensuring a task is only removed from the queue *after* successful completion. If a worker crashes mid-task, it is automatically re-queued.
- **Visibility Timeout**: Configured at 2 hours to ensure long-running document analysis tasks aren't accidentally redelivered.
- **Graceful Retries**: 
    - **Transient Errors** (Rate limits, timeouts): Automatically retried with **Exponential Backoff** (1m, 2m, 4m...).
    - **Permanent Errors** (Missing files, invalid formats): Gracefully failed and reported to the user to prevent queue clogging.

---

## ⚡ Optimization Techniques

- **Batch Embedding**: High-throughput vector generation using batch requests to AI providers, reducing network latency and overhead.
- **Lazy Loading**: Services are initialized only when needed (Lazy Singletons), reducing the initial memory footprint of the API and Workers.
- **Connection Pooling**: Optimized database and Redis connection pooling for high-concurrency workloads.

---

## 🏗️ Technical Stack

* **Backend**: FastAPI (Async Python 3.10+)
* **Task Queue**: Celery + Redis
* **Vector DB**: PostgreSQL + `pgvector` + `HNSW` Indexing
* **AI Engine**: Ollama (Local) & Gemini (Cloud)
* **Storage**: Multi-provider support (S3, R2, MinIO, Local FS)
* **OCR**: Tesseract OCR & Poppler

---

## 🛠️ Setup & Installation

### Prerequisites

1.  **Python 3.10+**
2.  **PostgreSQL** (with `pgvector` extension)
3.  **Redis** (for Celery)
4.  **Tesseract OCR** (`apt install tesseract-ocr`)
5.  **Ollama** (Required for local AI processing - [Download here](https://ollama.com/))

### Installation

1.  **Install Dependencies:**
    ```bash
    poetry install
    ```

2.  **Database Migration:**
    ```bash
    alembic upgrade head
    ```

3.  **Environment Setup:**
    Create a `.env` file from the example. Ensure `OLLAMA_BASE_URL` points to your local instance (usually `http://host.docker.internal:11434` if using Docker, or `http://localhost:11434` if bare-metal).

4.  **Running with Docker (Recommended):**
    ```bash
    docker-compose up -d --build
    ```

---

## 🧪 Testing

The project includes a full suite of unit and integration tests:
```bash
pytest
```

---

## 📚 API Reference (Core Routes)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/documents/upload` | Upload file, hash contents, and trigger RAG indexing. |
| **GET** | `/documents/` | List all processed documents. |
| **POST** | `/documents/{id}/query` | Ask questions to a specific document using RAG. |
| **GET** | `/documents/{id}` | Check processing status and view AI analysis. |
| **DELETE** | `/documents/{id}` | Wipe document, local file, cloud object, and vectors. |

---

## 🤝 Security

* **JWT Multi-Tenancy**: All data is strictly isolated by user ID.
* **File Validation**: Magic-byte checking prevents spoofed file uploads.
* **Rate Limiting**: Integrated protection against brute-force attacks on auth routes.
