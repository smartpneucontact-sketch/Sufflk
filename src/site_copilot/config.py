from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SITE_COPILOT_", env_file=".env", extra="ignore")

    anthropic_api_key: str | None = None
    model: str = "claude-sonnet-4-6"
    project_id: str = "demo-allerton-tower"

    retriever: str = "bm25"  # bm25 | hybrid
    top_k: int = 6

    corpus_dir: Path = Path("data/corpus")
    traces_dir: Path = Path("traces")

    use_mock_llm: bool = False
    max_agent_steps: int = 6


def get_settings() -> Settings:
    import os

    s = Settings()
    if s.anthropic_api_key is None:
        s.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    return s
