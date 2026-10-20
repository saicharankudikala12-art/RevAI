# RevAI - AI-Powered Last-Minute Exam Revision

RevAI is a specialized web application designed to help students revise efficiently when facing strict time constraints before an exam. Instead of skimming through hundreds of pages of unorganized notes or answering random questions, RevAI analyzes student-provided PDFs (question banks, previous exam papers, revision guides), factors in the student's remaining time, generates an optimized high-value revision test, evaluates test performance to detect weak concepts, and produces targeted flashcards for rapid final review.

---

## Technology Stack & Architectural Decisions

| Layer | Technology | Rationale |
|---|---|---|
| **Backend API** | **Python 3.14 + FastAPI** | High performance asynchronous ASGI framework with native type hints, automatic OpenAPI/Swagger documentation (`/docs`), and seamless readiness for AWS deployment (App Runner / ECS / Lambda). |
| **Data Validation** | **Pydantic v2 + Pydantic Settings** | Strict schema validation for all API inputs and outputs, ensuring predictable structured contracts between client and server. |
| **PDF Extraction Engine** | **pypdf** | Robust, native Python PDF parsing library capable of multi-page text extraction and reliable automatic page count detection without external binary dependencies. |
| **Configuration** | **python-dotenv / .env** | Strict isolation of application secrets and environment variables, keeping API keys and environment-specific settings out of source code. |
| **Testing** | **pytest + httpx TestClient** | Automated integration and unit testing for API endpoints and business logic. |
| **Frontend UI** | **Semantic HTML5 + Custom Vanilla CSS + ES6+ JavaScript** | Eliminates fragile frontend build dependencies and bloated node modules. Delivers instant load times, responsive mobile-ready design, and effortless hosting on AWS S3 + CloudFront CDN or static web servers. |

---

## Folder Structure

```
RevAI/
├── .gitignore                     # Production-grade gitignore for Python, OS, IDE, and secrets
├── .env.example                   # Root environment variables template
├── README.md                      # Complete project documentation and setup guide
│
├── backend/                       # Backend service package
│   ├── .env.example               # Backend-specific environment template
│   ├── requirements.txt           # Python dependencies
│   ├── app/
│   │   ├── __init__.py            # Application package initializer
│   │   ├── main.py                # FastAPI app entry point, CORS middleware, and lifespan
│   │   ├── core/                  # Core configuration
│   │   │   ├── __init__.py
│   │   │   └── config.py          # Environment settings with Pydantic Settings
│   │   ├── api/                   # API routing
│   │   │   ├── __init__.py
│   │   │   └── routes.py          # Central API router & health check endpoint
│   │   ├── models/                # Data models and schemas
│   │   │   ├── __init__.py
│   │   │   └── schemas.py         # Pydantic schemas (HealthResponse, APIErrorResponse)
│   │   └── services/              # Business logic services (modular stubs for future milestones)
│   │       └── __init__.py        # Houses pdf_service, ai_service, scoring_service, etc.
│   └── tests/                     # Automated test suite
│       ├── __init__.py
│       └── test_health.py         # Pytest verification for health and root endpoints
│
└── frontend/                      # Client-side web application
    ├── index.html                 # Semantic HTML5 layout with revision stepper and live diagnostics
    ├── css/
    │   ├── tokens.css             # Harmonious color tokens, typography scale, spacing, radii
    │   └── style.css              # Responsive layout, cards, badges, and interactive buttons
    └── js/
        ├── config.js              # Environment-aware API URL configuration
        ├── api.js                 # Modular fetch API client with latency tracking
        └── app.js                 # App initialization, live health checking, and DOM binding
```

---

## Installation & Setup Instructions

### Prerequisites
- **Python 3.10+** (Tested on Python 3.14.0)
- **Modern Web Browser** (Chrome, Firefox, Edge, Safari)
- **Git**

---

### Backend Setup

1. **Navigate to the project root**:
   ```bash
   cd RevAI
   ```

2. **Create a virtual environment**:
   - On Windows (PowerShell):
     ```powershell
     python -m venv backend/.venv
     backend\.venv\Scripts\Activate.ps1
     ```
   - On macOS/Linux:
     ```bash
     python3 -m venv backend/.venv
     source backend/.venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   # Copy example environment configuration
   cp backend/.env.example backend/.env
   ```

5. **Start the backend server**:
   - **Unified Serving (Serves both Web App & API)**:
     ```bash
     uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
     ```
     The entire app will be live at:
     - Web Application: `http://localhost:8000/`
     - Health Check: `http://localhost:8000/api/health`
     - Interactive OpenAPI (Swagger) Docs: `http://localhost:8000/docs`

   - **Development with hot reload**:
     ```bash
     uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
     ```

---

### Production Start Command

For unified production hosting (e.g. Render, Railway, AWS App Runner):
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2
```

---

### Frontend Setup (Decoupled Dev Option)

If developing frontend files separately from the backend:
1. Using Node's `npx serve`:
   ```bash
   npx serve frontend -l 5500
   ```
2. The frontend automatically detects decoupled dev ports (e.g., 5500, 3000) and routes API requests to `http://127.0.0.1:8000/api`. When served from port 8000 or any production domain, it seamlessly uses relative `/api` on the same origin.

---

## Running Automated Tests

Run the full backend test suite using `pytest`:

```powershell
# From project root
backend\.venv\Scripts\pytest backend/tests/ -v
```

---

## Deployment Readiness

RevAI is architected for unified, containerized, or cloud deployment:
- **Unified Web & API Service**: FastAPI serves static frontend files at root (`/`, `/css`, `/js`) and API routes under `/api`, eliminating CORS issues in production.
- **Stateless & Scalable**: No database required. Test tokens are HMAC-SHA256 signed. PDF processing is in-memory with zero disk persistence.
- **Environment & Secrets**: Configured via standard environment variables (`APP_ENV`, `SECRET_KEY`, `CORS_ORIGINS`, `ALLOW_HEURISTIC_FALLBACK`, `AI_API_KEY`). In production, a secure custom `SECRET_KEY` is strictly enforced at startup.

---

## Development Milestones Roadmap

- [x] **MILESTONE 1**: Project foundation and architecture (FastAPI backend, clean frontend, modular folders, Pydantic schemas, health check, automated tests, Git config).
- [x] **MILESTONE 2**: PDF upload and PDF text/page processing (`pypdf` extraction, page counting, validation).
- [x] **MILESTONE 3**: Revision settings UI and backend API (Time remaining & target question count).
- [x] **MILESTONE 4**: AI-powered revision test generation (Context-aware prompt generation, structured output).
- [x] **MILESTONE 5**: Test-taking interface (Interactive questions, option selection, timer).
- [x] **MILESTONE 6**: Scoring and results (Evaluation engine, accuracy metrics, explanations, HMAC tokens).
- [x] **MILESTONE 7**: Weak-topic analysis (Concept mapping and targeted remediation detection).
- [x] **MILESTONE 8**: AI-generated smart revision flashcards (Interactive 3D flip cards, recall tips, weak-topic focus).
