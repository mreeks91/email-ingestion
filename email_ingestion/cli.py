"""CLI entrypoint."""

from __future__ import annotations

import argparse
import time

from email_ingestion.config import load_config, AppConfig
from email_ingestion.pipeline.orchestrator import run_ingestion
from email_ingestion.util.logging import configure_logging
from email_ingestion.util.time import parse_datetime


def _build_config(base: AppConfig, args: argparse.Namespace) -> AppConfig:
    return AppConfig(
        db_url=args.db_url or base.db_url,
        storage_root=args.storage_root or base.storage_root,
        log_level=args.log_level or base.log_level,
        log_file=base.log_file,
        checkpoint_name=base.checkpoint_name,
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="email-ingest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run ingestion")
    run_parser.add_argument("--mailbox", required=True, help="Shared mailbox name")
    run_parser.add_argument("--folder", required=True, help="Folder path, e.g. Inbox/Subfolder")
    run_parser.add_argument("--since-checkpoint", action="store_true", help="Use stored checkpoint")
    run_parser.add_argument("--since", help="Override start datetime (ISO)")
    run_parser.add_argument("--limit", type=int, help="Max messages to process")
    run_parser.add_argument("--db-url", help="Database URL override")
    run_parser.add_argument("--storage-root", help="Storage root override")
    run_parser.add_argument("--log-level", help="Log level override")
    run_parser.add_argument("--poll-seconds", type=int, help="Poll interval in seconds")

    args = parser.parse_args()
    config = _build_config(load_config(), args)
    configure_logging(config.log_level, config.log_file)

    if args.command == "run":
        since_dt = parse_datetime(args.since)
        if args.poll_seconds:
            first = True
            while True:
                run_ingestion(
                    config=config,
                    mailbox=args.mailbox,
                    folder=args.folder,
                    since=since_dt if first else None,
                    limit=args.limit,
                    use_checkpoint=args.since_checkpoint or not first,
                )
                first = False
                time.sleep(args.poll_seconds)
        else:
            run_ingestion(
                config=config,
                mailbox=args.mailbox,
                folder=args.folder,
                since=since_dt,
                limit=args.limit,
                use_checkpoint=args.since_checkpoint,
            )


if __name__ == "__main__":
    main()
