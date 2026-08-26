"""
disable_all_fks.py — Disable every foreign-key constraint on a SQL Server database.

Why this exists
---------------
The Nitara BAM sync pipeline copies rows from the primary to a secondary
using `INSERT … SELECT … FROM [primary].[db].dbo.[table] WHERE NOT EXISTS
…`. If the destination DB has FKs enabled, child rows whose parent
hasn't been synced yet (or whose parent doesn't exist on the secondary
at all) will fail with error 547. The pipeline assumes FKs are off on
the destination; this script enforces that assumption.

Usage
-----
    # From CLI — explicit credentials
    python scripts/disable_all_fks.py --host 10.10.98.26 --port 31813 \\
        --user sa --password 'P@ssw0rd@123' --database NitaraDB

    # From CLI — read host/port/user/password/database from a Nitara BAM env
    python scripts/disable_all_fks.py --env uat

    # Dry-run — print what would change, no DDL
    python scripts/disable_all_fks.py --env uat --dry-run

    # Re-enable later (e.g. in QA where you want FKs back)
    python scripts/disable_all_fks.py --env uat --enable

Idempotent
----------
Re-running is safe: only currently-enabled FKs are touched, and
`is_disabled` is checked first. `sys.foreign_keys` is the source of
truth, so the script also works if FKs were enabled/disabled out of band.

Notes
-----
* Disabling with `NOCHECK CONSTRAINT` keeps the FK metadata intact — you
  can re-enable later with `CHECK CONSTRAINT`. New rows that violate the
  constraint will still be allowed while it's disabled.
* SQL Server also marks the FK `is_not_trusted=1` after `NOCHECK`. If you
  later want to re-enable and have the constraint actually enforced,
  run `ALTER TABLE … WITH CHECK CHECK CONSTRAINT …` first to validate
  existing data, otherwise the constraint stays "untrusted" and won't
  be enforced.
* This script does NOT touch check constraints, triggers, or indexes.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

try:
    import pyodbc
except ImportError:
    sys.exit("pyodbc is required: pip install pyodbc")


# ---------------------------------------------------------------------------
# Settings DB helpers (read the same env settings the Flask app uses)
# ---------------------------------------------------------------------------

REPO_ROOT     = Path(__file__).resolve().parent.parent
SETTINGS_DB   = REPO_ROOT / "settings.db"


def load_env_servers(env_value: str) -> list[dict]:
    """Return the servers list for the named env from settings.db."""
    if not SETTINGS_DB.exists():
        sys.exit(f"settings.db not found at {SETTINGS_DB}")
    con = sqlite3.connect(str(SETTINGS_DB))
    try:
        cur = con.cursor()
        cur.execute("SELECT settings_json FROM Environments WHERE value = ?", (env_value,))
        row = cur.fetchone()
        if not row:
            sys.exit(f"env {env_value!r} not found in {SETTINGS_DB}")
        env = json.loads(row[0])
        return env.get("servers", []) or []
    finally:
        con.close()


def conn_str(host: str, port: str | int, user: str, password: str, database: str) -> str:
    return (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={host},{port};DATABASE={database};"
        f"UID={user};PWD={password};"
        f"TrustServerCertificate=yes;Encrypt=yes;"
    )


# ---------------------------------------------------------------------------
# FK enumerate / mutate
# ---------------------------------------------------------------------------

def list_fks(cur) -> list[dict]:
    cur.execute("""
        SELECT
            fk.name                                  AS fk_name,
            OBJECT_NAME(fk.parent_object_id)         AS parent_table,
            SCHEMA_NAME(fk.schema_id)                AS parent_schema,
            OBJECT_NAME(fk.referenced_object_id)     AS referenced_table,
            fk.is_disabled                           AS is_disabled,
            fk.is_not_trusted                        AS is_not_trusted
        FROM sys.foreign_keys fk
        ORDER BY parent_schema, parent_table, fk_name
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def set_fk(cur, fk: dict, enable: bool) -> tuple[bool, str]:
    """Toggle one FK. Returns (changed, message)."""
    verb = "CHECK" if enable else "NOCHECK"
    sql = (
        f"ALTER TABLE [{fk['parent_schema']}].[{fk['parent_table']}] "
        f"{verb} CONSTRAINT [{fk['fk_name']}]"
    )
    try:
        cur.execute(sql)
        return True, sql
    except Exception as e:
        return False, f"{sql}  →  {e}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Disable or re-enable every foreign-key on a SQL Server DB."
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--env", help="Read server creds from settings.db for this env "
                                  "(uses the env's SECONDARY — first non-primary).")
    src.add_argument("--host", help="DB host (or IP). Use with --port/--user/--password/--database.")

    p.add_argument("--port",      type=str, default="1433")
    p.add_argument("--user",      type=str)
    p.add_argument("--password",  type=str)
    p.add_argument("--database",  type=str, default="NitaraDB")

    p.add_argument("--dry-run",   action="store_true",
                   help="Print what would change, do not issue any DDL.")
    p.add_argument("--enable",    action="store_true",
                   help="Re-enable FKs (CHECK CONSTRAINT) instead of disabling them.")
    p.add_argument("--server",    choices=["primary", "secondary", "all"], default="secondary",
                   help="When using --env, which server(s) to target. Default: secondary.")
    return p.parse_args()


def resolve_target(args) -> list[dict]:
    """Return the list of {host,port,user,password,database,label} dicts to process."""
    if args.host:
        if not (args.user and args.password):
            sys.exit("--user and --password are required when --host is given")
        return [{
            "label": f"{args.host}:{args.port}",
            "host": args.host, "port": args.port,
            "user": args.user, "password": args.password,
            "database": args.database,
        }]

    # --env path
    servers = load_env_servers(args.env)
    if not servers:
        sys.exit(f"env {args.env!r} has no servers")
    out = []
    for s in servers:
        if args.server == "primary"   and not s.get("isPrimary"):  continue
        if args.server == "secondary" and     s.get("isPrimary"):  continue
        out.append({
            "label": f"{s['server']}:{s.get('port','1433')}",
            "host":  s["server"],
            "port":  s.get("port", "1433"),
            "user":  s["user"],
            "password": s["password"],
            "database":  s.get("db", "NitaraDB"),
        })
    if not out:
        sys.exit(f"no matching server(s) for env={args.env!r} server={args.server!r}")
    return out


def main() -> int:
    args = parse_args()
    verb = "ENABLE" if args.enable else "DISABLE"
    targets = resolve_target(args)

    overall_changed = 0
    overall_skipped = 0
    overall_failed   = 0
    overall_total    = 0

    for t in targets:
        print(f"\n{'='*70}\n{t['label']} / {t['database']}  ({verb}{', DRY-RUN' if args.dry_run else ''})\n{'='*70}")
        try:
            cnx = pyodbc.connect(
                conn_str(t["host"], t["port"], t["user"], t["password"], t["database"]),
                autocommit=True, timeout=15,
            )
        except Exception as e:
            print(f"  ❌ CONNECT FAILED: {e}")
            overall_failed += 1
            continue
        try:
            cur = cnx.cursor()
            fks = list_fks(cur)
            enabled   = [f for f in fks if not f["is_disabled"]]
            disabled  = [f for f in fks if     f["is_disabled"]]
            print(f"  total FKs: {len(fks)}  (enabled: {len(enabled)}, disabled: {len(disabled)})")

            to_change = enabled if not args.enable else disabled
            if not to_change:
                print(f"  nothing to {verb.lower()} — all FKs already in target state")
            else:
                print(f"  {verb} plan ({len(to_change)} FKs):")
                changed = 0
                failed  = 0
                for fk in to_change:
                    overall_total += 1
                    if args.dry_run:
                        print(f"    [DRY-RUN] {fk['parent_schema']}.{fk['parent_table']}.{fk['fk_name']}")
                        continue
                    ok, msg = set_fk(cur, fk, enable=args.enable)
                    if ok:
                        changed += 1
                        overall_changed += 1
                    else:
                        failed  += 1
                        overall_failed += 1
                        print(f"    ❌ {msg}")
                action = "would change" if args.dry_run else "changed"
                print(f"  {action}: {changed}, failed: {failed}, "
                      f"skipped (already in target state): {len(fks) - len(to_change)}")
        finally:
            cnx.close()

    print(f"\n{'='*70}")
    print(f"TOTAL: {verb}{'d' if not args.dry_run else ' (DRY-RUN)'} on "
          f"{len(targets)} server(s) — changed: {overall_changed}, "
          f"failed: {overall_failed}, already-in-state: {overall_skipped}, "
          f"total-seen: {overall_total}")
    return 0 if overall_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
