# Email Ingestion Pipeline (Outlook via win32com)

Local Windows pipeline that reads a shared Outlook mailbox using `pywin32` MAPI (no Graph, no OAuth), normalizes content, routes attachments to pluggable heads, and persists results.

## Quick Start
1. Install dependencies.
2. Configure `.env` from `.env.example`.
3. Run:

```powershell
email-ingest run --mailbox "Shared Mailbox Name" --folder "Inbox/Folder" --since-checkpoint
```

To poll periodically in-process:

```powershell
email-ingest run --mailbox "Shared Mailbox Name" --folder "Inbox/Folder" --since-checkpoint --poll-seconds 300
```

## Notes
- Requires Outlook installed on the host and access to the mailbox.
- Idempotent by deterministic IDs + upserts.
