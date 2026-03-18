"""FastAPI entrypoint.

This module is intentionally lightweight; pure business logic lives in app.application.
"""

from pathlib import Path

try:
    from dotenv import load_dotenv

    # Load .env from project root (two levels up from this file)
    _env_path = Path(__file__).resolve().parents[2] / ".env"
    if not _env_path.exists():
        _env_path = Path(__file__).resolve().parents[3] / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:  # pragma: no cover - dependency is not installed in this environment.
    FastAPI = None
    CORSMiddleware = None

from app.api.routes.health import health_payload
from app.api.routes.runs import create_run, get_run, list_runs, refine_run


def create_app():
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Install project dependencies to run the API.")

    app = FastAPI(title="Event Surge Activation Copilot API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    def health_check():
        return health_payload()

    @app.post("/api/v1/runs")
    def create_run_endpoint(payload: dict):
        return create_run(payload)

    @app.get("/api/v1/runs/{run_id}")
    def get_run_endpoint(run_id: str):
        return get_run(run_id)

    @app.get("/api/v1/runs")
    def list_runs_endpoint():
        return list_runs()

    @app.post("/api/v1/runs/{run_id}/refine")
    def refine_run_endpoint(run_id: str, payload: dict):
        return refine_run(run_id, payload)

    return app


app = create_app() if FastAPI is not None else None
