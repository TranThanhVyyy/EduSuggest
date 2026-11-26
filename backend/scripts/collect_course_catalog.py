"""Inventory EduSuggest and maintain the cited public-source registry.

This command is read-only with respect to PostgreSQL.  It records aggregate
counts and schema metadata only; it deliberately excludes account PII and
course bodies from the inventory report.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import inspect, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.official_dataset_common import (
    EXPECTED_REVISION,
    PRODUCTION_DATABASE,
    REPORT_DIR,
    SOURCE_MANIFEST,
    assert_database_target,
    create_database_engine,
    ensure_generated_directories,
    write_json,
)

COLLECTED_AT = "2026-11-26"

SOURCES = [
    {
        "name": "Khóa Học Nhanh – Công nghệ thông tin",
        "url": "https://khoahocnhanh.com/courses?category=cong-nghe-thong-tin",
        "type": "public course metadata/taxonomy reference",
        "license": "No reuse license verified; titles/topics used only for market taxonomy review",
        "usage": "No paid video, cover, instructor identity, or proprietary outline copied",
    },
    {
        "name": "freeCodeCamp curriculum",
        "url": "https://www.freecodecamp.org/learn/",
        "type": "public curriculum taxonomy reference",
        "license": "Repository content subject to freeCodeCamp open-source licensing",
        "usage": "Topic sequencing reference; EduSuggest lesson prose is original",
    },
    {
        "name": "Microsoft Learn training",
        "url": "https://learn.microsoft.com/training/",
        "type": "official training catalog reference",
        "license": "Microsoft site terms; no content copied",
        "usage": "Level, role and subject taxonomy reference",
    },
    {
        "name": "MIT OpenCourseWare",
        "url": "https://ocw.mit.edu/",
        "type": "open educational resource reference",
        "license": "CC BY-NC-SA 4.0 for OCW materials unless a page states otherwise",
        "usage": "Links may be cited; no MIT name/logo used to imply endorsement",
    },
    {
        "name": "MDN Web Docs",
        "url": "https://developer.mozilla.org/",
        "type": "official web-platform documentation",
        "license": "See MDN content license on the referenced page",
        "usage": "External reference URL only",
    },
    {
        "name": "Python documentation",
        "url": "https://docs.python.org/3/",
        "type": "official language documentation",
        "license": "Python Software Foundation documentation license",
        "usage": "External reference URL only",
    },
    {
        "name": "PostgreSQL documentation",
        "url": "https://www.postgresql.org/docs/",
        "type": "official database documentation",
        "license": "PostgreSQL license/documentation terms",
        "usage": "External reference URL only",
    },
    {
        "name": "Vue documentation",
        "url": "https://vuejs.org/guide/",
        "type": "official framework documentation",
        "license": "MIT-licensed project; documentation terms apply",
        "usage": "External reference URL only",
    },
    {
        "name": "React documentation",
        "url": "https://react.dev/learn",
        "type": "official framework documentation",
        "license": "React site/project terms",
        "usage": "External reference URL only",
    },
    {
        "name": "roadmap.sh",
        "url": "https://roadmap.sh/",
        "type": "public role/topic roadmap reference",
        "license": "Site/project license; no diagrams copied",
        "usage": "Coverage-gap review only",
    },
    {
        "name": "Kaggle Learn",
        "url": "https://www.kaggle.com/learn",
        "type": "public data-learning catalog reference",
        "license": "Kaggle terms; no course content copied",
        "usage": "Data/ML topic taxonomy reference",
    },
    {
        "name": "Cisco Networking Academy",
        "url": "https://www.netacad.com/",
        "type": "public networking/security catalog reference",
        "license": "Cisco terms; no course content copied",
        "usage": "Networking/security topic coverage reference",
    },
]


def collect_inventory(database: str) -> dict:
    engine = create_database_engine(database)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text("SET TRANSACTION READ ONLY"))
            assert_database_target(
                connection,
                expected_database=database,
                expected_revision=EXPECTED_REVISION,
            )
            inspector = inspect(connection)
            tables = sorted(inspector.get_table_names(schema="public"))
            counts: dict[str, int] = {}
            table_metadata: dict[str, dict] = {}
            for table in tables:
                quoted = connection.dialect.identifier_preparer.quote(table)
                counts[table] = int(
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {quoted}"
                    ).scalar_one()
                )
                table_metadata[table] = {
                    "columns": [
                        column["name"] for column in inspector.get_columns(table)
                    ],
                    "primary_key": inspector.get_pk_constraint(table).get(
                        "constrained_columns", []
                    ),
                    "foreign_keys": [
                        {
                            "columns": item.get("constrained_columns", []),
                            "target_table": item.get("referred_table"),
                            "target_columns": item.get("referred_columns", []),
                        }
                        for item in inspector.get_foreign_keys(table)
                    ],
                    "unique_constraints": [
                        item.get("column_names", [])
                        for item in inspector.get_unique_constraints(table)
                    ],
                }
            result = {
                "collected_at": datetime.now(UTC).isoformat(),
                "database": database,
                "revision": EXPECTED_REVISION,
                "table_count": len(tables),
                "record_counts": counts,
                "schema": table_metadata,
                "read_only": True,
                "pii_included": False,
            }
            transaction.rollback()
            return result
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=PRODUCTION_DATABASE)
    parser.add_argument(
        "--inventory-output",
        type=Path,
        default=REPORT_DIR / "production-inventory.json",
    )
    parser.add_argument("--sources-output", type=Path, default=SOURCE_MANIFEST)
    args = parser.parse_args()

    ensure_generated_directories()
    write_json(
        args.sources_output,
        {
            "collected_at": COLLECTED_AT,
            "method": "Manual review of public pages; no authenticated scraping",
            "sources": SOURCES,
        },
    )
    inventory = collect_inventory(args.database)
    write_json(args.inventory_output, inventory)
    print(
        f"READ-ONLY inventory complete: database={inventory['database']} "
        f"revision={inventory['revision']} tables={inventory['table_count']}"
    )
    for table, count in inventory["record_counts"].items():
        print(f"  {table}: {count}")
    print(f"Inventory: {args.inventory_output}")
    print(f"Sources: {args.sources_output}")


if __name__ == "__main__":
    main()
