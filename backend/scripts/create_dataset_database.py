"""Create or normalize the isolated dataset staging database; never drop one."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text

from scripts.official_dataset_common import (
    DATASET_STAGING_DATABASE,
    create_database_engine,
)


def main() -> None:
    engine = create_database_engine("postgres").execution_options(
        isolation_level="AUTOCOMMIT"
    )
    try:
        with engine.connect() as connection:
            names = set(
                connection.execute(
                    text(
                        "SELECT datname FROM pg_database "
                        "WHERE datname IN (:exact_name, :folded_name)"
                    ),
                    {
                        "exact_name": DATASET_STAGING_DATABASE,
                        "folded_name": DATASET_STAGING_DATABASE.lower(),
                    },
                ).scalars()
            )
            if DATASET_STAGING_DATABASE in names:
                print(f"Database already exists: {DATASET_STAGING_DATABASE}")
                return
            folded = DATASET_STAGING_DATABASE.lower()
            if folded in names:
                # This specific folded name is produced by an earlier quoting
                # mistake in our own prepare script.  Rename preserves the empty
                # database and avoids a destructive DROP.
                connection.exec_driver_sql(
                    f'ALTER DATABASE "{folded}" RENAME TO "{DATASET_STAGING_DATABASE}"'
                )
                print(f"Normalized database name: {folded} -> {DATASET_STAGING_DATABASE}")
                return
            connection.exec_driver_sql(
                f'CREATE DATABASE "{DATASET_STAGING_DATABASE}" WITH ENCODING \'UTF8\''
            )
            print(f"Created database: {DATASET_STAGING_DATABASE}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
