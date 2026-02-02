"""Configuration loading for the ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AppConfig:
    db_url: str
    storage_root: str
    log_level: str = "INFO"
    checkpoint_name: str = "outlook_default"


def load_config() -> AppConfig:
    db_url = os.getenv("EMAIL_INGEST_DB_URL", "sqlite:///email_ingest.db")
    storage_root = os.getenv("EMAIL_INGEST_STORAGE_ROOT", r"C:\email_ingest_storage")
    log_level = os.getenv("EMAIL_INGEST_LOG_LEVEL", "INFO")
    checkpoint_name = os.getenv("EMAIL_INGEST_CHECKPOINT", "outlook_default")
    return AppConfig(
        db_url=db_url,
        storage_root=storage_root,
        log_level=log_level,
        checkpoint_name=checkpoint_name,
    )
