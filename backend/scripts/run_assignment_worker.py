"""Safe standalone launcher for the PostgreSQL assignment queue worker.

This GĐ3.8.1 launcher is deliberately restricted to EduSuggest_phase3_test.
It never mutates project .env and never starts from FastAPI import/lifespan.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Settings.DEBUG in the existing .env contains a non-boolean legacy value.
# This worker does not need SQL debug logging; override this process only.
os.environ["DEBUG"] = "False"

from config.config import get_settings
from service.assignment_worker import AssignmentQueueWorker

EXPECTED_TEST_DATABASE = "EduSuggest_phase3_test"
ALLOWED_TEST_DATABASES = frozenset({"EduSuggest_phase3_test", "EduSuggest_phase4_test"})
RETRY_DELAYS_SECONDS = (5, 15, 30, 60)


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


def configure_logging(log_path: Path | None) -> None:
    handler: logging.Handler
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_path, encoding="utf-8")
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def emit(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    exc_info = bool(fields.pop("exc_info", False))
    logger.log(level, event, extra={"event": event, "fields": fields}, exc_info=exc_info)


def _unlink_control_file(path: Path | None, logger: logging.Logger, worker_id: str) -> None:
    """Best-effort cleanup for transient Windows file-sharing locks."""
    if path is None:
        return
    for attempt in range(5):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError:
            if attempt < 4:
                time.sleep(0.1 * (attempt + 1))
    emit(
        logger,
        logging.WARNING,
        "worker_control_file_cleanup_deferred",
        worker_id=worker_id,
        file_name=path.name,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-database",
        "--expected-db",
        dest="expected_database",
        required=True,
        help="Fail closed unless PostgreSQL reports this exact test database.",
    )
    parser.add_argument("--poll-interval", "--poll-seconds", dest="poll_interval", type=float, default=5.0)
    parser.add_argument("--lease-seconds", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--log-file", type=Path, default=None)
    parser.add_argument("--control-dir", type=Path, default=None)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one real worker tick and exit; intended for integration checks.",
    )
    parser.add_argument(
        "--allow-multiple",
        action="store_true",
        help="Compatibility flag for intentional multi-worker operation.",
    )
    args = parser.parse_args()
    if not 0.2 <= args.poll_interval <= 60:
        parser.error("--poll-interval must be between 0.2 and 60 seconds")
    if args.lease_seconds < 5 or args.batch_size < 1:
        parser.error("lease must be >= 5 seconds and batch size >= 1")
    return args


def main() -> int:
    args = _parse_args()
    configure_logging(args.log_file)
    logger = logging.getLogger("edusuggest.assignment_worker")
    worker_id = args.worker_id or f"worker-{os.getpid()}"
    settings = get_settings()

    if args.expected_database not in ALLOWED_TEST_DATABASES:
        emit(
            logger,
            logging.CRITICAL,
            "worker_db_guard_abort",
            worker_id=worker_id,
            expected_database=args.expected_database,
            allowed_databases=sorted(ALLOWED_TEST_DATABASES),
        )
        return 3

    required_flags = {
        "AUTO_ASSIGNMENT_WORKFLOW_ENABLED": settings.auto_assignment_workflow_enabled,
        "AUTO_ASSIGNMENT_WORKER_ENABLED": settings.auto_assignment_worker_enabled,
        "ACCOUNTABILITY_ENABLED": settings.accountability_enabled,
    }
    disabled = [key for key, enabled in required_flags.items() if not enabled]
    if disabled:
        emit(logger, logging.ERROR, "worker_refused_flag_disabled", worker_id=worker_id, disabled=disabled)
        return 2

    configured_url = make_url(settings.database_url.get_secret_value())
    if configured_url.database not in ({"EduSuggest"} | ALLOWED_TEST_DATABASES):
        emit(
            logger,
            logging.ERROR,
            "worker_start_rejected_configured_database",
            worker_id=worker_id,
            configured_database=configured_url.database,
        )
        return 2
    target_url = configured_url.set(database=args.expected_database)

    engine = create_engine(
        target_url,
        pool_pre_ping=True,
        hide_parameters=True,
        pool_size=2,
        max_overflow=2,
    )
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with engine.connect() as conn:
            actual_db = conn.execute(text("SELECT current_database()")).scalar_one()
            if actual_db != args.expected_database:
                emit(
                    logger,
                    logging.CRITICAL,
                    "worker_database_guard_failed",
                    worker_id=worker_id,
                    expected_database=args.expected_database,
                    actual_database=actual_db,
                )
                return 3

        control_dir = args.control_dir
        pid_file: Path | None = None
        stop_file: Path | None = None
        if control_dir:
            control_dir.mkdir(parents=True, exist_ok=True)
            pid_file = control_dir / f"worker-{os.getpid()}.pid"
            stop_file = control_dir / f"worker-{os.getpid()}.stop"
            pid_file.write_text(
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "worker_id": worker_id,
                        "started_at": datetime.now(UTC).isoformat(),
                        "database": actual_db,
                    }
                ),
                encoding="utf-8",
            )

        stop_event = threading.Event()

        def request_stop(signum: int, _frame: Any) -> None:
            emit(logger, logging.INFO, "worker_shutdown_signal", worker_id=worker_id, signal=signum)
            stop_event.set()

        for sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            sig = getattr(signal, sig_name, None)
            if sig is not None:
                try:
                    signal.signal(sig, request_stop)
                except (OSError, ValueError):
                    pass

        worker = AssignmentQueueWorker(
            sessions,
            worker_id=worker_id,
            lease_seconds=args.lease_seconds,
            batch_size=args.batch_size,
            expected_db_name=args.expected_database,
        )
        emit(
            logger,
            logging.INFO,
            "worker_started",
            worker_id=worker_id,
            database=actual_db,
            workflow_enabled=True,
            worker_enabled=True,
            accountability_enabled=True,
            poll_interval_seconds=args.poll_interval,
            once=args.once,
        )

        consecutive_errors = 0
        tick = 0
        while not stop_event.is_set():
            if stop_file and stop_file.exists():
                emit(logger, logging.INFO, "worker_stop_requested", worker_id=worker_id)
                break
            tick += 1
            try:
                summary = worker.run_once()
                outcomes = summary.get("outcomes", [])
                outcome_summaries = [
                    {
                        "job_id": outcome.jobId,
                        "queue_status": outcome.finalQueueStatus,
                        "assignment_status": outcome.assignmentStatus,
                        "assignment_id": outcome.assignmentId,
                        "fenced_out": outcome.fencedOut,
                    }
                    for outcome in outcomes
                ]
                emit(
                    logger,
                    logging.INFO,
                    "worker_tick_completed",
                    worker_id=worker_id,
                    tick=tick,
                    reclaimed=summary["reclaimed"],
                    expired=summary["expired"],
                    ended_pauses=summary["ended_pauses"],
                    recovered_violations=summary["recovered_violations"],
                    revoked=summary["revoked"],
                    claimed=summary["claimed"],
                    outcomes=outcome_summaries,
                )
                consecutive_errors = 0
            except Exception as exc:  # noqa: BLE001 - durable lease recovery handles process/database faults
                delay = RETRY_DELAYS_SECONDS[min(consecutive_errors, len(RETRY_DELAYS_SECONDS) - 1)]
                consecutive_errors += 1
                emit(
                    logger,
                    logging.ERROR,
                    "worker_tick_failed_retrying",
                    worker_id=worker_id,
                    error_type=type(exc).__name__,
                    retry_in_seconds=delay,
                    exc_info=True,
                )
                if args.once:
                    return 4
                deadline = time.monotonic() + delay
                while time.monotonic() < deadline and not stop_event.is_set():
                    if stop_file and stop_file.exists():
                        break
                    stop_event.wait(min(0.25, max(0.0, deadline - time.monotonic())))
                continue
            if args.once:
                break
            stop_event.wait(args.poll_interval)

        emit(logger, logging.INFO, "worker_stopped", worker_id=worker_id, ticks=tick)
        return 0
    finally:
        _unlink_control_file(pid_file if "pid_file" in locals() else None, logger, worker_id)
        _unlink_control_file(stop_file if "stop_file" in locals() else None, logger, worker_id)
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
