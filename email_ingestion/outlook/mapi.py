"""MAPI helpers for Outlook."""

from __future__ import annotations

from typing import Iterable
import logging

logger = logging.getLogger(__name__)


def get_namespace():
    try:
        import win32com.client  # type: ignore
    except Exception as exc:  # pragma: no cover - platform specific
        raise RuntimeError("pywin32 is required to use Outlook MAPI") from exc
    outlook = win32com.client.Dispatch("Outlook.Application")
    return outlook.GetNamespace("MAPI")


def _list_folder_names(folder) -> list[str]:
    try:
        return [f.Name for f in folder.Folders]
    except Exception:
        return []


def resolve_shared_folder(namespace, mailbox: str, folder_path: str):
    try:
        root = namespace.Folders.Item(mailbox)
    except Exception as exc:
        available = [f.Name for f in namespace.Folders]
        raise ValueError(
            f"Mailbox '{mailbox}' not found. Available top-level folders: {available}"
        ) from exc
    folder = root
    if folder_path:
        normalized = folder_path.replace("\\", "/")
        parts = [part for part in normalized.split("/") if part]
        current_path = mailbox
        for part in parts:
            try:
                folder = folder.Folders.Item(part)
            except Exception as exc:
                available = _list_folder_names(folder)
                raise ValueError(
                    f"Folder '{part}' not found under '{current_path}'. Available: {available}"
                ) from exc
            current_path = f"{current_path}/{part}"
    return folder
