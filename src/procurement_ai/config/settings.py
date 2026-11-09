"""Application settings using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/procurement"
    vector_db_url: str = "postgresql+asyncpg://user:pass@localhost:5432/procurement"

    # LLM Provider
    llm_provider: str = "openai"  # openai | ollama
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # Embeddings (local by default so no API key is required)
    embedding_provider: str = "sentence_transformers"  # openai | sentence_transformers
    embedding_model: str = "all-MiniLM-L6-v2"

    # LangSmith (optional tracing)
    langsmith_api_key: str = ""
    langsmith_tracing: bool = False
    langsmith_project: str = "procurement-ai"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "change-me-in-production-use-32-chars-min"
    access_token_expire_minutes: int = 480

    # MCP Server
    mcp_server_url: str = "http://localhost:8001"

    # Conversation memory (Postgres-backed chat threads)
    chat_memory_enabled: bool = True

    # Planner: deterministic | llm
    planner_mode: str = "deterministic"
    opencode_go_api_key: str = ""
    opencode_go_base_url: str = "https://opencode.ai/zen/go/v1"
    opencode_go_model: str = "claude-haiku-5-5"
    opencode_session_id: str = "procurement-ai-planner"
    llm_timeout_seconds: float = 20.0

    # Observability
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    prometheus_port: int = 9090
    grafana_port: int = 3001

    # Retrieval
    retrieval_top_k: int = 20
    reranking_enabled: bool = False  # cross-encoder adds latency; enable explicitly
    reranking_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Anomaly Detection
    anomaly_ml_enabled: bool = True
    anomaly_contamination: float = 0.05

    # Approval
    approval_low_risk_max: float = 10000
    approval_medium_risk_max: float = 50000


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
