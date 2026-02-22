## FieldOps AI Backend (FastAPI)

This directory contains the FastAPI backend for the SpeedRun/FieldOps AI project.

### Environment variables

The backend **loads configuration from the `.env` file** in this directory (and from the process environment). See `config.py`: it calls `load_dotenv()`, so **`.env` is the main environment file** for local development.

**Variables read from `.env` (or env):**

- `OPENAI_API_KEY` — API key for OpenAI (required for AI features, no default).
- `DATABASE_URL` — SQLAlchemy database URL.  
  - Default: `sqlite:///./fieldops.db` (local SQLite file in the backend directory).
  - For Postgres on Render, use `postgresql://USER:PASSWORD@HOST:PORT/DBNAME` (or the connection string Render provides).
- `LABOR_RATE_PER_HOUR` — Default labor rate used for job costing (default: `75.00`).
- `LOW_STOCK_THRESHOLD` — Inventory low-stock threshold (default: `5`).
- `FRONTEND_URL` — URL of the frontend used for CORS and links (default: `http://localhost:3000`).
- `OLLAMA_MODEL` — Local model name if you wire this up to an Ollama instance (default: `llama3.2`).

Create a `.env` file in this directory and set the variables above (at minimum `OPENAI_API_KEY` and `DATABASE_URL` if not using the default SQLite).

### Local development

From the `backend` directory:

1. (Optional but recommended) Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # on Linux/macOS
   # .venv\Scripts\activate   # on Windows PowerShell
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Ensure your `.env` file or shell exports the necessary environment variables (at minimum `OPENAI_API_KEY` and `DATABASE_URL` if you are not using the default SQLite DB).

4. Run the FastAPI app with Uvicorn in **dev mode**:

   ```bash
   # from within backend/
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

5. Visit:

   - API root: `http://localhost:8000/`
   - OpenAPI docs: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/api/health`

On startup, `init_db()` in `database.py` runs `Base.metadata.create_all(bind=engine)`, so your tables will be created automatically using the configured `DATABASE_URL`.

### Production runtime (e.g., Render)

In production you typically run without `--reload` and bind to the host/port provided by the platform.

Example command (Render Web Service, where `$PORT` is injected by the platform):

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Before starting the service, make sure the following env vars are set in your hosting provider’s dashboard:

- `OPENAI_API_KEY`
- `DATABASE_URL` (pointing to your managed database, e.g. Render PostgreSQL)
- `LABOR_RATE_PER_HOUR` (optional override)
- `LOW_STOCK_THRESHOLD` (optional override)
- `FRONTEND_URL` (set to your Vercel frontend URL once deployed)
- `OLLAMA_MODEL` (if used)

This matches the expectations in `config.py` and `database.py` and is safe for both local and production deployment.

