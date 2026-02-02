# Email Ingestion Pipeline (Local Outlook via win32com)

## 0) Hard Constraints (Do Not Violate)
- **Must use local Outlook access via `win32com` / `pywin32`**.
- **Must NOT require Microsoft Graph API**, OAuth app registration, or tenant-level permissions.
- Runs on a Windows machine with Outlook installed and access to the shared mailbox.
- Polls periodically (scheduler/cron/Task Scheduler) and is safe to run repeatedly (idempotent).

## 1) Objective
Ingest heterogeneous emails from a **shared team mailbox** into a database for downstream analytics/ML.
Emails may include:
- attachments: `.docx`, `.pptx`, `.pdf`, images, `.msg` (email message attachments)
- inline images / embedded content
- calendar invites (`.ics`, meeting requests): need meeting date/time + attendee/organizer + attachments
- links in body (potentially relevant)
- tables and structured text inside attachments

We need a consistent ingestion + processing architecture with pluggable “heads” per content type.

## 2) High-Level Pipeline Stages
1. **Fetch** (Outlook via win32com):
   - Enumerate items from target mailbox folder(s).
   - Use a watermark / checkpoint to avoid reprocessing.
   - Capture email metadata + raw body (plain + HTML) where available.
   - Save attachments/inline content to disk (content-addressed).

2. **Normalize**:
   - Normalize bodies to text (keep HTML raw as well).
   - Extract links from HTML/text.
   - Detect calendar invites and parse meeting details.
   - Identify inline images + map to content IDs.

3. **Process Content (“Heads”)**:
   - Route attachments and inline content to processors by MIME/type/extension.
   - Each head emits:
     - extracted text
     - extracted tables (where feasible)
     - extracted images (if embedded)
     - structured metadata (e.g., meeting start/end)
     - errors/warnings (non-fatal)

4. **Persist**:
   - Store normalized email record, attachment records, extracted artifacts, and processing logs.
   - Maintain stable IDs + deduplication.
   - Record processing status per item/head.

## 3) Architectural Principles
- **Idempotent**: repeated runs must not duplicate records.
- **Deterministic IDs**:
  - Prefer Outlook identifiers where stable (EntryID + StoreID), but assume they may change if moved/copied.
  - Also compute content hashes (SHA-256) for attachments and (normalized) email content.
- **Pluggable Heads**:
  - Each head implements a common interface.
  - Heads are independently testable.
- **No ad hoc parsing in the fetch layer**:
  - Fetch stores raw + basic normalized fields; heavy parsing is in processors.
- **Strong observability**:
  - Structured logs, run IDs, per-head timing, per-item error capture.

## 4) Data Model (Minimum Viable)
Tables (or equivalents):
- `ingestion_runs`: run_id, started_at, finished_at, stats, host
- `emails`:
  - email_id (PK), source_system='outlook', outlook_entry_id, outlook_store_id,
  - received_at, sent_at, subject, sender_name, sender_email,
  - to/cc/bcc (normalized), conversation_id (if available),
  - body_text_raw, body_text_normalized, body_html, link_list (json), is_calendar, calendar_start, calendar_end, ...
  - raw_headers (optional), processing_state
- `attachments`:
  - attachment_id (PK), email_id (FK), filename, ext, mime,
  - sha256, size_bytes, saved_path, is_inline, content_id
- `extracted_artifacts`:
  - artifact_id, email_id, attachment_id (nullable),
  - artifact_type: 'text'|'table'|'image'|'calendar'|'link'|'msg_embedded'...
  - payload (json), text (nullable), file_path (nullable), metadata (json)
- `processing_events`:
  - event_id, run_id, email_id, attachment_id, head_name,
  - status: success|error|skipped, error_message, metrics(json), created_at

## 5) Processing Heads (Initial Set)
- `EmailBodyHead`:
  - HTML->text normalization, link extraction, quoted-reply trimming (optional).
- `CalendarInviteHead`:
  - Detect meeting requests / `.ics`.
  - Extract start/end/timezone, organizer, attendees, location, join links.
- `DocxHead`:
  - Extract text + tables.
- `PptxHead`:
  - Extract slide text + speaker notes.
- `PdfHead`:
  - Extract text + tables where possible.
- `ImageHead`:
  - For inline images and attached images, store + (optional) OCR hook later.
- `MsgHead`:
  - Parse attached `.msg` recursively into an email-like record or artifact.

Non-goals for v1:
- Perfect OCR / perfect PDF table extraction.
- Full fidelity rendering.
- Real-time streaming ingestion (polling is fine).

## 6) Implementation Notes / win32com Specifics
- Use Outlook MAPI to open the shared mailbox and target folder(s).
- Support:
  - items: MailItem, MeetingItem, ReportItem (as encountered)
  - attachments: normal + inline (ContentID), `.msg` attachments
- Store raw bodies (HTML + plain) and attachment binaries on disk.
- Avoid UI prompts: run Outlook in a context that doesn’t trigger dialogs; handle security prompts if any via IT-approved policy.

## 7) Quality Bar / Acceptance Criteria
- Given a mailbox folder with mixed emails:
  - pipeline ingests items without duplicates across runs
  - attachments saved and hashed
  - calendar invites produce correct start/end
  - `.docx/.pptx/.pdf` produce extracted text artifacts
  - failures don’t halt the run; errors captured per item/head
- Unit tests for:
  - routing logic
  - heads on sample files
  - dedup + idempotency behavior

## 8) Package Layout (Implemented)
- `email_ingestion/outlook/`: MAPI fetcher for shared mailbox folders.
- `email_ingestion/normalize/`: body + calendar normalization helpers.
- `email_ingestion/heads/`: pluggable processors per content type.
- `email_ingestion/storage/`: content-addressed storage (sha256).
- `email_ingestion/db/`: SQLAlchemy models + repository layer.
- `email_ingestion/pipeline/`: router + orchestrator.
- `email_ingestion/cli.py`: `email-ingest run` entrypoint.
