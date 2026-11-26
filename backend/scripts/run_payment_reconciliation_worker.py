"""GĐ4.7A.2 Standalone Durable Payment Reconciliation Worker Launcher.

Strictly separated from GĐ3 run_assignment_worker.py.
- Requires PAYMENT_RECONCILIATION_WORKER_ENABLED=True.
- Enforces explicit --expected-database allowlist (NEVER touches Production EduSuggest by mistake).
- Runs schema_guard fail-closed check before polling.
- Supports graceful SIGINT/SIGTERM shutdown, --once, and structured JSON logs without secrets.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import signal
import sys
import threading
import time
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["DEBUG"] = "False"

from config.config import get_settings
from config.schema_guard import SchemaCompatibilityError, verify_database_schema_compatibility
from service.payment_reconciliation_worker import (
    PaymentReconciliationWorker,
    sweep_stale_payment_tasks,
)

ALLOWED_TEST_DATABASES = frozenset({"EduSuggest_phase4_test", "EduSuggest_phase47a2_rehearsal"})


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def emit(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    logger.log(level, event, extra={"event": event, "fields": fields})


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EduSuggest Durable Payment Reconciliation Worker")
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--lease-seconds", type=int, default=60)
    parser.add_argument("--sweep-interval", type=float, default=60.0)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    logger = logging.getLogger("edusuggest.payment_reconciliation_worker")

    worker_id = args.worker_id or f"pay-recon-{os.getpid()}"
    settings = get_settings()

    if args.expected_database not in ALLOWED_TEST_DATABASES:
        emit(
            logger,
            logging.CRITICAL,
            "payment_worker_db_guard_abort",
            worker_id=worker_id,
            expected_database=args.expected_database,
            allowed_databases=sorted(ALLOWED_TEST_DATABASES),
        )
        return 3

    if not settings.payment_reconciliation_worker_enabled:
        emit(
            logger,
            logging.ERROR,
            "payment_worker_flag_disabled",
            worker_id=worker_id,
            flag="PAYMENT_RECONCILIATION_WORKER_ENABLED",
        )
        return 2

    configured_url = make_url(settings.database_url.get_secret_value())
    target_url = configured_url.set(database=args.expected_database)
    engine = create_engine(target_url, pool_pre_ping=True, hide_parameters=True, pool_size=2, max_overflow=2)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    try:
        with engine.connect() as conn:
            actual_db = str(conn.execute(text("SELECT current_database()")).scalar_one() or "")
            if actual_db != args.expected_database:
                emit(logger, logging.CRITICAL, "payment_worker_db_mismatch", expected=args.expected_database, actual=actual_db)
                return 3

        verify_database_schema_compatibility(engine, require_marketplace_tables=True)

        stop_event = threading.Event()

        def _handle_stop(signum: int, _frame: Any) -> None:
            emit(logger, logging.INFO, "payment_worker_signal_received", worker_id=worker_id, signal=signum)
            stop_event.set()

        signal.signal(signal.SIGINT, _handle_stop)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _handle_stop)

        worker = PaymentReconciliationWorker(sessions, worker_id=worker_id, lease_seconds=args.lease_seconds)
        emit(logger, logging.INFO, "payment_worker_started", worker_id=worker_id, database=args.expected_database)

        last_sweep = 0.0
        while not stop_event.is_set():
            now_mono = time.monotonic()
            if now_mono - last_sweep >= args.sweep_interval:
                with sessions() as db:
                    enqueued = sweep_stale_payment_tasks(db)
                if enqueued:
                    emit(logger, logging.INFO, "payment_worker_swept", worker_id=worker_id, enqueued=enqueued)
                last_sweep = now_mono

            outcome = worker.run_once()
            if outcome is not None:
                emit(logger, logging.INFO, "payment_worker_processed", worker_id=worker_id, outcome=outcome)
            if args.once:
                break
            if outcome is None:
                stop_event.wait(timeout=max(0.2, args.poll_interval))

        emit(logger, logging.INFO, "payment_worker_stopped", worker_id=worker_id)
        return 0
    except SchemaCompatibilityError as exc:
        emit(logger, logging.CRITICAL, "payment_worker_schema_incompatible", worker_id=worker_id, error=str(exc))
        return 4
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
