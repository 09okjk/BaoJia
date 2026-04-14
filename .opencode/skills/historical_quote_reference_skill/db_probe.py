from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parents[1] / ".env"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe PostgreSQL schema for history skill."
    )
    parser.add_argument(
        "--mode",
        choices=["tables", "columns", "sample"],
        default="tables",
        help="Probe mode",
    )
    parser.add_argument("--table", help="Table name for columns/sample mode")
    args = parser.parse_args()

    _load_env_file(ENV_PATH)
    conn = psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )
    try:
        with conn.cursor() as cur:
            if args.mode == "tables":
                cur.execute(
                    """
                    select table_schema, table_name
                    from information_schema.tables
                    where table_schema not in ('pg_catalog', 'information_schema')
                    order by table_schema, table_name
                    """
                )
                print(json.dumps(cur.fetchall(), ensure_ascii=False, indent=2))
                return

            if not args.table:
                raise ValueError("--table is required for columns/sample mode")

            if args.mode == "columns":
                cur.execute(
                    """
                    select table_schema, table_name, column_name, data_type
                    from information_schema.columns
                    where table_name = %s
                    order by ordinal_position
                    """,
                    (args.table,),
                )
                print(json.dumps(cur.fetchall(), ensure_ascii=False, indent=2))
                return

            cur.execute(f'SELECT * FROM "{args.table}" LIMIT 3')
            rows = cur.fetchall()
            column_names = [desc.name for desc in cur.description]
            payload = [dict(zip(column_names, row, strict=False)) for row in rows]
            print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    finally:
        conn.close()


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_key = key.strip()
        if not env_key or env_key in os.environ:
            continue
        os.environ[env_key] = value.strip().strip('"').strip("'")


if __name__ == "__main__":
    main()
