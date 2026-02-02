"""MAPI helpers for Outlook."""

from __future__ import annotations

from typing import Iterable


def get_namespace():
    try:
        import win32com.client  # type: ignore
    except Exception as exc:  # pragma: no cover - platform specific
        raise RuntimeError("pywin32 is required to use Outlook MAPI") from exc
    outlook = win32com.client.Dispatch("Outlook.Application")
    return outlook.GetNamespace("MAPI")


def resolve_shared_folder(namespace, mailbox: str, folder_path: str):
    root = namespace.Folders.Item(mailbox)
    folder = root
    if folder_path:
        parts = [part for part in folder_path.split("/") if part]
        for part in parts:
            folder = folder.Folders.Item(part)
    return folder
