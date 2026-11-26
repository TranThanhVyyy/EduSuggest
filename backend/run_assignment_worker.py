"""Compatibility entrypoint for the official assignment worker launcher.

The implementation lives in scripts.run_assignment_worker. This wrapper preserves
the original command while preventing two launcher implementations from drifting.
"""
from scripts.run_assignment_worker import main


if __name__ == "__main__":
    raise SystemExit(main())
