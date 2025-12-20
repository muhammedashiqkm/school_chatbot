# Syllabus Q\&A Chatbot (RAG System)

A production-ready backend service that answers questions about school/college syllabi and course documents using Retrieval-Augmented Generation (RAG).

Built with **FastAPI**, **PostgreSQL (pgvector)**, **Celery**, and **Gemini/OpenAI**.

## 🚀 Features

  * **RAG Pipeline:** PDF ingestion, text chunking, and vector search.
  * **Asynchronous Processing:** Celery + Redis for background PDF processing.
  * **Vector Search:** PostgreSQL with `pgvector` for efficient similarity search.
  * **Multi-LLM Support:** Chat via Gemini, OpenAI, or DeepSeek.
  * **Strict Embeddings:** Uses Google Gemini (`text-embedding-004`) for low-cost, high-performance embeddings (768 dimensions).
  * **Admin Dashboard:** Flask-Admin interface for managing users, schools, and documents.
  * **Secure:** JWT Authentication for API, Session-based auth for Admin.

## 🛠 Tech Stack

  * **API:** FastAPI (Async)
  * **Database:** PostgreSQL + pgvector
  * **ORM:** SQLAlchemy (Async + Sync)
  * **Task Queue:** Celery + Redis
  * **LLM Integration:** Google GenAI SDK / OpenAI SDK
  * **Admin UI:** Flask-Admin

-----

## 📋 Prerequisites

1.  **PostgreSQL (External):** You must have a PostgreSQL instance running.
2.  **Redis:** Required for the task queue.
3.  **Python 3.10+** (if running locally).
4.  **Docker & Docker Compose** (recommended for deployment).

### Database Setup

Before running the app, connect to your PostgreSQL database and enable the vector extension:

```sql
CREATE EXTENSION vector;
```

*Note: This project is configured for **768 dimensions** (Gemini Embeddings).*

-----

## ⚙️ Configuration

Create a `.env` file in the root directory:

```properties
PROJECT_NAME=SyllabusQA
API_V1_STR=/api/v1
SECRET_KEY=super_secure_random_string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database (Ensure this points to your external DB)
# For Docker: Use 'host.docker.internal' to access host DB on Mac/Windows, or the IP on Linux.
POSTGRES_SERVER=host.docker.internal
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword
POSTGRES_DB=syllabus_qa
POSTGRES_PORT=5432

# Derived Connection Strings
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_SERVER}:${POSTGRES_PORT}/${POSTGRES_DB}
DATABASE_URL_SYNC=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_SERVER}:${POSTGRES_PORT}/${POSTGRES_DB}

# Redis
REDIS_URL=redis://redis:6379/0

# LLM Keys
# REQUIRED for Embeddings and RAG
GEMINI_API_KEY=AIzaSy... 
# Optional (if using these models for Chat)
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...

# Storage
UPLOAD_FOLDER=./uploads
```

-----

## 🐳 Running with Docker (Recommended)

This setup runs the API and the Celery Worker. It assumes the Database is hosted externally (AWS RDS, or a local Postgres instance).

1.  **Build and Start:**

    ```bash
    docker-compose up --build -d
    ```

2.  **Check Logs:**

    ```bash
    docker-compose logs -f
    ```

The API will be available at `http://localhost:8000`.

-----

## 💻 Running Locally (Development)

1.  **Install Dependencies:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # or venv\Scripts\activate on Windows
    pip install -r requirements.txt
    ```

2.  **Start Redis:**
    Ensure Redis is running locally on port 6379.

3.  **Start Celery Worker:**

    ```bash
    celery -A app.worker.tasks.celery_app worker --loglevel=info
    ```

4.  **Start FastAPI Server:**

    ```bash
    uvicorn main:app --reload
    ```

-----

## 🔐 First Run: Create Admin User

To access the Admin Panel (`/admin`), you need a superuser. Run the included script:

**Docker:**

```bash
docker-compose exec api python scripts/create_superuser.py --username admin --password securepass
```

**Local:**

```bash
python scripts/create_superuser.py --username admin --password securepass
```

-----

## 📖 API Documentation

Once running, access the interactive Swagger documentation:

  * **URL:** `http://localhost:8000/docs`

### Key Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/login` | Get JWT Access Token |
| `POST` | `/api/v1/schools` | Setup School, Class, and Subjects |
| `POST` | `/api/v1/document` | Upload PDF or URL for ingestion |
| `POST` | `/api/v1/chat` | Ask questions (RAG) |
| `DELETE` | `/document/{id}` | Remove document |

-----

## 🧠 Architecture

### Folder Structure

```text
syllabus_qa/
├── app/
│   ├── api/          # Route controllers
│   ├── core/         # Config, Logging, Security
│   ├── db/           # Database connection & Models
│   ├── models/       # SQLAlchemy Tables
│   ├── schemas/      # Pydantic Models
│   ├── services/     # Business Logic (RAG, Auth, Ingestion)
│   ├── worker/       # Celery Tasks
│   └── admin/        # Flask-Admin Views
├── logs/             # Application logs
├── scripts/          # Utility scripts
└── main.py           # Application Entrypoint
```

### Ingestion Pipeline

1.  **Upload:** User uploads PDF or provides URL.
2.  **Task Queue:** API saves metadata and pushes ID to Redis.
3.  **Processing (Celery):**
      * Downloads PDF.
      * Extracts text.
      * Splits into chunks (1000 chars).
      * **Embeds:** Uses `Gemini text-embedding-004` (768 dim).
      * **Saves:** Stores vectors in Postgres (`pgvector`).

### RAG Chat Pipeline

1.  **Query:** User sends question + filters (School/Class).
2.  **Embed:** Question is embedded using Gemini.
3.  **Search:** System performs Cosine Similarity search in Postgres.
4.  **Generate:** Top 5 chunks + Question sent to LLM (Gemini/OpenAI/Deepseek).
5.  **Response:** Answer returned to user.