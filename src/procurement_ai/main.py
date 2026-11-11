"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from procurement_ai.api.routes import anomalies, approvals, auth, chat, decisions, health
from procurement_ai.config.settings import get_settings
from procurement_ai.graph.action_execution import close_action_graph
from procurement_ai.observability.http_metrics import MetricsMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Iris")
    yield
    await close_action_graph()
    logger.info("Shutting down Iris")


app = FastAPI(
    title="Iris — Procurement Intelligence & Operations Platform",
    description=(
        "Natural-language interface for procurement operations with "
        "evidence-backed answers, anomaly detection, and human-in-the-loop workflows."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(anomalies.router, prefix="/anomalies", tags=["anomalies"])
app.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
app.include_router(decisions.router, prefix="/decisions", tags=["decisions"])


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics in text exposition format."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    return {
        "name": "Iris — Procurement Intelligence & Operations Platform",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }
