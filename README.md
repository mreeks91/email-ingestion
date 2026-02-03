# Email Ingestion Pipeline (Outlook via win32com)

Local Windows pipeline that reads a shared Outlook mailbox using `pywin32` MAPI (no Graph, no OAuth), normalizes content, routes attachments to pluggable heads, and persists results.

**Prerequisites**
- Windows machine with Outlook installed and a profile that can access the shared mailbox.
- Python 3.10+.
- Network access to the mailbox (on-prem or Exchange Online via Outlook).

**Install**
1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install the package and dependencies:

```powershell
pip install -e .
```

3. Optional: install `.msg` support:

```powershell
pip install -e ".[msg]"
```

**Configure**
1. Copy `.env.example` to `.env` and update values as needed:
   - `EMAIL_INGEST_DB_URL` for database connection.
   - `EMAIL_INGEST_STORAGE_ROOT` for attachment storage.
   - `EMAIL_INGEST_LOG_LEVEL` for verbosity.

2. Ensure the storage root directory exists or can be created.

**Run Once**
Run with a shared mailbox and folder path:

```powershell
email-ingest run --mailbox "Shared Mailbox Name" --folder "Inbox/Folder" --since-checkpoint
```

Run with an explicit start time (ISO-8601):

```powershell
email-ingest run --mailbox "Shared Mailbox Name" --folder "Inbox/Folder" --since "2026-02-01T00:00:00"
```

Limit to N most recent items:

```powershell
email-ingest run --mailbox "Shared Mailbox Name" --folder "Inbox/Folder" --limit 50
```

**Poll Periodically**
To poll every 5 minutes in-process:

```powershell
email-ingest run --mailbox "Shared Mailbox Name" --folder "Inbox/Folder" --since-checkpoint --poll-seconds 300
```

Notes on polling:
- The first iteration can honor `--since` or `--since-checkpoint`.
- Subsequent iterations always use the stored checkpoint to fetch only new items.

**Database and Storage**
- SQLite is the default for local development.
- Attachments and inline images are stored in content-addressed storage by `sha256`.
- Idempotency is enforced via deterministic IDs and upserts.

**Troubleshooting**
- If Outlook security prompts appear, ensure the profile is trusted and configured by IT policy.
- If no items are found, verify mailbox name and folder path.
- If `.msg` parsing fails, confirm the optional `extract-msg` dependency is installed.
