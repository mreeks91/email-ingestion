"""Content-addressed storage for attachments and blobs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from email_ingestion.util.hashing import sha256_bytes


@dataclass(frozen=True)
class StoredFile:
    sha256: str
    path: Path
    size_bytes: int


class ContentAddressedStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root)

    def _path_for(self, sha256: str, ext: str | None) -> Path:
        safe_ext = ""
        if ext:
            ext = ext.lower()
            if not ext.startswith("."):
                ext = f".{ext}"
            safe_ext = ext
        return self.root / sha256[:2] / sha256[2:4] / f"{sha256}{safe_ext}"

    def store_bytes(self, data: bytes, ext: str | None = None) -> StoredFile:
        digest = sha256_bytes(data)
        path = self._path_for(digest, ext)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
        size = path.stat().st_size
        return StoredFile(sha256=digest, path=path, size_bytes=size)

    def ensure_root(self) -> None:
        os.makedirs(self.root, exist_ok=True)
