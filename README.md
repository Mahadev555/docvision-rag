# DocVision-RAG
### Vision-Enhanced Multimodal RAG for Intelligent Document Understanding

## Overview

Traditional RAG ignores everything in a PDF that isn't plain text — diagrams, architecture visuals, flowcharts and screenshots are invisible to it. DocVision fixes that:

1. Parse a PDF into clean Markdown with **PyMuPDF4LLM**, extracting every embedded image along the way.
2. Upload each image to **Cloudinary** and send it to **Gemini Vision** for a structured, detailed analysis (not just a one-line caption).
3. Inject that analysis back into the Markdown, exactly where the image originally appeared.
4. Chunk the enriched Markdown (header-aware, token-bounded, with overlap) and embed it with **gemini-embedding-001**.
5. Store embeddings in **PostgreSQL + PGVector**.
6. At chat time, retrieve relevant chunks, generate an answer with **Gemini 2.5 Flash**, and return the answer alongside its source pages and any relevant images.

The result: diagrams and screenshots become searchable, right alongside the text.

---

## Demo

![Demo](docs/demo.png)
Chat answering a question grounded in a diagram, with cited pages and rank-ordered result images.

---

## Architecture

![Architecture](docs/architecture.png)

```
PDF Upload
   |
   v
PyMuPDF4LLM  ->  Markdown + Extracted Images
   |
   v
For each image: Upload to Cloudinary -> Analyse with Gemini Vision (structured JSON)
   |
   v
Inject rendered analysis back into Markdown (in place)
   |
   v
Markdown-aware chunking (headers, token budget, overlap)
   |
   v
Embed chunks (gemini-embedding-001) -> Store in PGVector
   |
   v
Chat: embed query -> vector search -> Gemini answer -> sources + images
```

---

## UI Tour

![Upload](docs/upload.png)
Drag-and-drop PDF upload with live background-processing status.

![Chat](docs/chat.png)
The chat interface with example RAG questions to get started.

![Dashboard](docs/dashboard.png)
Document dashboard — status, page/image/chunk counts, and per-document image previews.

---

## Features

- PDF -> Markdown conversion with full image extraction
- Structured (not one-line) image understanding via Gemini Vision
- Image analysis injected back into Markdown in place, tied to page number
- Markdown-aware chunking that preserves header hierarchy
- Semantic search over PGVector with cosine similarity
- Metadata filtering (scope retrieval to specific documents)
- Chat answers include cited sources (document + page) and relevant images
- Background processing: upload returns immediately, ingestion runs async
- Streaming chat responses (SSE)
- Conversation history persisted across turns
- Document deletion (cascades chunks/images, cleans up Cloudinary)

---

## Tech Stack

| Layer | Choice |
|---|---|
| API | FastAPI, Pydantic v2 |
| Database | PostgreSQL + PGVector, SQLAlchemy 2.0 (async), Alembic |
| PDF parsing | PyMuPDF4LLM, PyMuPDF |
| Vision & chat | Google Gemini 2.5 Flash |
| Embeddings | Google gemini-embedding-001 |
| Image storage | Cloudinary |
| Runtime | Python 3.12, Docker / Docker Compose |

---

## Repository Structure

Kept deliberately flat and easy to navigate — no repository-pattern layers or provider abstractions, just routes calling services directly.

```
app/
  config.py          # Settings, loaded from .env
  logger.py           # Logging setup
  exceptions.py        # AppError + its meaning
  database.py         # Engine, session, declarative Base
  constants.py         # Shared enums (DocumentStatus, ChatRole, ...)
  main.py            # FastAPI app, middleware, error handler, router mounting

  models/            # SQLAlchemy ORM models
    document.py
    image.py
    chunk.py
    chat.py

  schemas/            # Pydantic request/response models
    document.py
    chat.py
    vision.py         # ImageAnalysis structured schema + markdown renderer

  routes/            # API endpoints
    documents.py        # upload, list, get, delete
    chat.py            # RAG chat
    health.py          # /health

  services/            # All business logic and external integrations
    document_service.py    # CRUD, upload validation
    ingestion_service.py    # orchestrates the full pipeline
    chat_service.py       # retrieval + generation + history
    pdf_service.py        # PyMuPDF4LLM parsing + analysis injection
    chunking_service.py     # markdown-aware chunker
    vision_service.py      # Gemini Vision wrapper
    embedding_service.py    # Gemini embeddings wrapper
    llm_service.py        # Gemini chat wrapper
    storage_service.py     # Cloudinary wrapper
    vectorstore_service.py   # PGVector similarity search

  utils/
    retry.py            # async retry decorator
    tokens.py           # token counting (tiktoken)

alembic/              # DB migrations
docker/              # Dockerfile + entrypoint
tests/
```

---

## Setup

You need three things before the app can actually process a PDF: a **Gemini API key**, **Cloudinary credentials**, and a **Postgres database with the `vector` extension**. The steps below use [uv](https://github.com/astral-sh/uv) for Python dependency management and [Neon](https://neon.tech) (free tier, pgvector built in) for the database — this exact combination has been run end-to-end and verified working.

### 1. Get your credentials

- **Gemini API key** — https://aistudio.google.com/apikey (free tier available)
- **Cloudinary** — sign up at https://cloudinary.com/console, then from the Dashboard grab: Cloud Name, API Key, API Secret
- **Postgres + pgvector** — either:
  - **Neon** (recommended, no local install): create a project at https://neon.tech, copy the **direct** (non-`-pooler`) connection string from the dashboard
  - or run Postgres locally via Docker Compose (see step 4 below)

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
```env
GEMINI_API_KEY=your-gemini-api-key
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# If using Neon, uncomment and fill this in (note the +asyncpg driver and ssl=require):
DATABASE_URL=postgresql+asyncpg://user:password@your-neon-host/dbname?ssl=require
```
If `DATABASE_URL` is set, it takes priority over the discrete `POSTGRES_*` fields.

### 3. Install dependencies and create the schema

```bash
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt   # Windows
# uv pip install --python .venv/bin/python -r requirements-dev.txt        # macOS/Linux

.venv/Scripts/python.exe -m alembic upgrade head   # Windows
# .venv/bin/python -m alembic upgrade head          # macOS/Linux
```
This creates all 5 tables (`documents`, `chunks`, `images`, `conversations`, `chat_messages`) and enables the `vector` extension.

### 4. Run the app

```bash
.venv/Scripts/python.exe -m uvicorn app.main:app --reload   # Windows
# .venv/bin/uvicorn app.main:app --reload                   # macOS/Linux
```
API available at `http://localhost:8000`, interactive docs at `http://localhost:8000/docs`. Sanity-check with:
```bash
curl http://localhost:8000/api/v1/health
```

### Alternative: Docker Compose (self-hosted Postgres)

If you'd rather not use Neon, `docker-compose.yml` spins up a local `pgvector/pgvector` Postgres container alongside the API, running migrations automatically on boot:
```bash
docker compose up --build
```

---

## API

Interactive docs at `/docs` (Swagger) once running. Summary:

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/documents/upload` | Upload a PDF; returns immediately, processes in background |
| GET | `/api/v1/documents` | List documents (paginated) |
| GET | `/api/v1/documents/{id}` | Document detail + extracted images |
| DELETE | `/api/v1/documents/{id}` | Delete a document and all derived data |
| POST | `/api/v1/chat` | Ask a question (`stream: true` for SSE) |
| GET | `/api/v1/health` | Liveness/readiness |

### Chat response shape

```json
{
  "answer": "...",
  "conversation_id": "...",
  "sources": [{ "document": "spec.pdf", "page": 5, "score": 0.83 }],
  "images": [{ "url": "https://res.cloudinary.com/...", "page": 5, "description": "..." }]
}
```

### Document status lifecycle

`queued -> processing -> completed | failed`

---

## Future Improvements

- Hybrid search (vector + keyword/BM25)
- Queue-backed background processing (Celery/Arq) instead of in-process tasks, for horizontal scaling
- Per-document access control
- Table-specific extraction (beyond image-based analysis)

---

Made with 🧠❤️ by Mahadev Manerikar
