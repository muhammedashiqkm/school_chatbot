```markdown
# Syllabus QA - AI-Powered Academic Assistant

Syllabus QA is an AI-powered academic assistant designed to help students and teachers interact with their specific curriculum. It allows admins to upload textbooks (PDFs), which are processed and indexed for retrieval. Users can then chat with the system to get answers strictly based on their syllabus using Retrieval-Augmented Generation (RAG).

## 🚀 Features

* **RAG Architecture:** Answers are grounded strictly in uploaded textbook content to prevent hallucinations.
* **Multi-Model Support:** Integrates with **Gemini**, **OpenAI**, and **Deepseek**.
* **Smart Ingestion:** Automatically processes PDFs into vector embeddings using `pgvector`.
* **Hierarchical Content:** Organizes data via a strict `School > Syllabus > Class > Subject` hierarchy.
* **Hybrid Admin Panel:**
    * **FastAPI** for high-performance API endpoints.
    * **Flask-Admin** for a robust, user-friendly content management dashboard.
* **Role-Based Access:** Secure endpoints with JWT authentication.

---

## 🛠️ Tech Stack

* **Backend:** Python 3.12+, FastAPI, Flask
* **Database:** PostgreSQL (with `pgvector` extension), SQLAlchemy (Async & Sync)
* **Migrations:** Alembic
* **Task Queue:** Celery, Redis
* **Containerization:** Docker, Docker Compose

---

## ⚙️ Setup & Installation

### 1. Prerequisites

* Docker & Docker Compose installed.
* A `.env` file in the root directory.

### 2. Environment Variables (`.env`)

Create a file named `.env` in the root directory with the following configuration:

```properties
PROJECT_NAME="Syllabus QA"
API_V1_STR="/api/v1"

# Database Connection
# Note: Host is 'db' when running inside Docker, 'localhost' if running locally
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/syllabusqa
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:password@db:5432/syllabusqa
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY="change_this_to_a_secure_random_string"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_HOURS=24

# AI Keys (At least one is required)
GEMINI_API_KEY="your_gemini_key"
OPENAI_API_KEY="your_openai_key"
DEEPSEEK_API_KEY="your_deepseek_key"

# Model Configuration
GEMINI_MODEL_NAME="gemini-2.0-flash"
GEMINI_EMBEDDING_MODEL_NAME="models/gemini-embedding-001"

```

### 3. Run with Docker

Build and start the services:

```bash
docker-compose up --build

```

### 4. Database Initialization (Migrations)

Since automatic initialization is disabled, you must run Alembic migrations to create the database tables and the vector extension.

Run the following command inside the running API container:

```bash
docker-compose exec api alembic upgrade head

```

### 5. Create Superuser (Admin Access)

To log in to the Admin Panel (`/admin`), you must create a superuser account.

```bash
docker-compose exec api python create_superuser.py

```

Follow the prompts to set a username and password.

---

## 📚 API Documentation

All endpoints are prefixed with `/api/v1`.

### 🔐 Authentication

#### Login

**POST** `/login`
Returns a JWT token required for Authorization headers (`Authorization: Bearer <token>`).

* **Request Body:**
```json
{
  "username": "admin",
  "password": "securepassword"
}

```


* **Response:** `{"access_token": "...", "token_type": "bearer"}`

---

### 🏫 Schools & Hierarchy

#### Setup School Structure

**POST** `/schools`
Initialize metadata for a school. This establishes the valid dropdown options for documents.

* **Body:**
```json
{
  "school_name": "Greenwood High",
  "syllabus": ["CBSE", "ICSE"],
  "class": ["Class 10", "Class 12"],
  "subject": ["Physics", "Math"],
  "user_type": "teacher"
}

```



---

### 📄 Document Management

#### 1. Create Document via URL

Registers a document from a remote URL. The backend downloads and ingests it.

* **Endpoint:** `POST /document/url`
* **Body (JSON):**
```json
{
  "url": "[https://example.com/physics_10.pdf](https://example.com/physics_10.pdf)",
  "display_name": "Physics Chapter 1",
  "school": "Greenwood High",
  "syllabus": "CBSE",
  "class_name": "Class 10",
  "subject": "Physics"
}

```



#### 2. Create Document via File Upload

Uploads a local PDF file. Metadata is passed as a **JSON string** in the `body` form field.

* **Endpoint:** `POST /document/upload`
* **Content-Type:** `multipart/form-data`
* **Form Data:**
* `file`: (Binary PDF file)
* `body`: (Stringified JSON)
```json
{
  "display_name": "Physics Chapter 1",
  "school": "Greenwood High",
  "syllabus": "CBSE",
  "class_name": "Class 10",
  "subject": "Physics"
}

```





#### 3. View Document PDF

Streams the actual PDF file to the browser.

* **Endpoint:** `GET /document/{doc_id}/view`
* **Response:** Binary PDF stream (or `404 Not Found` if file is missing/URL-based).

#### 4. Update Document File

Replaces the file of an existing document ID.

* **Behavior:** Deletes the old file, saves the new one, and triggers re-ingestion (re-embedding). The Document UUID remains the same.
* **Endpoint:** `PUT /document/{doc_id}/upload`
* **Form Data:**
* `file`: (Binary PDF file)
* `body`: (Optional JSON string to update metadata)



#### 5. Update Document URL/Metadata

Updates the URL or metadata of a document.

* **Behavior:** If URL changes, deletes the local file (if any) and triggers re-ingestion.
* **Endpoint:** `PUT /document/{doc_id}/url`
* **Body:**
```json
{
  "url": "[https://new-url.com/file.pdf](https://new-url.com/file.pdf)",
  "display_name": "Updated Title",
  "school": "Greenwood High",
  "syllabus": "CBSE",
  "class_name": "Class 10",
  "subject": "Physics"
}

```



#### 6. Search Subjects

Returns available subjects for a specific Class/Syllabus combination (used for UI dropdowns).

* **Endpoint:** `POST /document/subject/search`
* **Body:**
```json
{
  "school": "Greenwood High",
  "syllabus": "CBSE",
  "class_name": "Class 10"
}

```



#### 7. List Documents

Filter documents by hierarchy.

* **Endpoint:** `POST /document_details`
* **Body:**
```json
{
  "college": "Greenwood High",
  "syllabus": "CBSE",      // Optional
  "class_name": "Class 10" // Optional
}

```



#### 8. Delete Document

Deletes the database record and removes the physical file from the disk.

* **Endpoint:** `DELETE /document/{doc_id}`

---

### 💬 Chat (RAG)

#### Send Message

Interacts with the AI using the context of the uploaded documents.

* **Endpoint:** `POST /chat`
* **Body:**
```json
{
  "chatbot_user_id": "session_123",
  "question": "What is Newton's Second Law?",
  "syllabus": "CBSE",
  "class_name": "Class 10",
  "subject": "Physics",
  "model": "gemini"
}

```



#### Clear Session

Resets conversation history for the session.

* **Endpoint:** `POST /clear_session`
* **Body:**
```json
{
  "chatbot_user_id": "session_123"
}

```



---

## 🖥️ Admin Panel

Access the dashboard at: **`http://localhost:8000/admin`**

* **Login:** Use credentials created via `create_superuser.py`.
* **Capabilities:**
* **Manage Hierarchy:** Create/Edit Schools, Syllabi, Classes, and Subjects.
* **Document Oversight:** Monitor ingestion status (`PENDING`, `COMPLETED`, `FAILED`).
* **Manual Overrides:** Edit document metadata or upload replacement files directly via the visual interface.
* **Security:** Authentication protected with Flash message error handling.



```

```