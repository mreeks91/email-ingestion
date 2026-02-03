"""Repository layer for database access."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import socket
import uuid

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from email_ingestion.db.models import (
    IngestionRun,
    Email,
    Attachment,
    ExtractedArtifact,
    ProcessingEvent,
    Checkpoint,
)


@dataclass(frozen=True)
class RunHandle:
    run_id: str


class Repository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def start_run(self) -> RunHandle:
        run_id = uuid.uuid4().hex
        run = IngestionRun(
            run_id=run_id,
            started_at=datetime.utcnow(),
            host=socket.gethostname(),
        )
        self.session.add(run)
        self.session.commit()
        return RunHandle(run_id=run_id)

    def finish_run(self, run_id: str, stats: dict | None = None) -> None:
        stmt = (
            update(IngestionRun)
            .where(IngestionRun.run_id == run_id)
            .values(finished_at=datetime.utcnow(), stats=stats)
        )
        self.session.execute(stmt)
        self.session.commit()

    def upsert_email(self, payload: dict) -> str:
        stmt = sqlite_insert(Email).values(**payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Email.email_id],
            set_=payload,
        )
        self.session.execute(stmt)
        self.session.commit()
        return payload["email_id"]

    def upsert_attachment(self, payload: dict) -> str:
        stmt = sqlite_insert(Attachment).values(**payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Attachment.attachment_id],
            set_=payload,
        )
        self.session.execute(stmt)
        self.session.commit()
        return payload["attachment_id"]

    def add_artifact(self, payload: dict) -> None:
        if "metadata" in payload and "artifact_metadata" not in payload:
            payload["artifact_metadata"] = payload.pop("metadata")
        stmt = sqlite_insert(ExtractedArtifact).values(**payload)
        stmt = stmt.on_conflict_do_nothing(index_elements=[ExtractedArtifact.artifact_id])
        self.session.execute(stmt)
        self.session.commit()

    def add_processing_event(self, payload: dict) -> None:
        stmt = sqlite_insert(ProcessingEvent).values(**payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=[ProcessingEvent.event_id],
            set_=payload,
        )
        self.session.execute(stmt)
        self.session.commit()

    def get_checkpoint(self, name: str) -> str | None:
        stmt = select(Checkpoint).where(Checkpoint.name == name)
        result = self.session.execute(stmt).scalar_one_or_none()
        return result.value if result else None

    def set_checkpoint(self, name: str, value: str) -> None:
        stmt = sqlite_insert(Checkpoint).values(name=name, value=value)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Checkpoint.name],
            set_={"value": value},
        )
        self.session.execute(stmt)
        self.session.commit()
