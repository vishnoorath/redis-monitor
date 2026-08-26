"""
Install the missing sync-related SPs on PROD secondaries.

Run via: wsl -u root -d Ubuntu -- python3 /tmp/install_prod_sps.py

What it deploys (per secondary), with DROP+CREATE pattern for safety:
  - usp_GenerateSyncScript_VR_Dispatcher   (the one PROD is missing -> 2812)
  - usp_GenerateSyncScript_VR_CLR          (the CLR-aware variant)
  - usp_GenerateSyncScript_VR              (re-deploy in case it has changed)
  - usp_GetMissingRows_CLR                 (re-deploy in case it has changed)
  - ClrColumnOverrides seed (table CREATE IF NOT EXISTS + Farms overrides)

The primary (10.10.98.47) already has all the SPs (per the earlier check),
so we don't touch it.

Each .sql file uses `CREATE PROCEDURE`. We prepend a `DROP PROCEDURE IF EXISTS`
batch so the deploy is fully idempotent and re-runnable.
"""
import os
import re
import sys
import pyodbc
from pathlib import Path

# PROD env (from .env / settings.db)
PROD_PRIMARY = ('10.10.98.47', '1433', 'sa', 't5!bT5AZ5Q@coqZ', 'NitaraDB')
PROD_SECONDARIES = [
    ('10.10.98.66',  '1433', 'sa', 'Gt(#@987HaS',   'NitaraDB'),
    ('10.10.98.76',  '1433', 'sa', 'Gt(#@987RTGF',  'NitaraDB'),
    ('10.10.98.100', '1433', 'sa', 'P@ssw0rd@123',  'NitaraDB'),
]

SQL_DIR = Path('/mnt/c/Users/VISHNOORATH/code/gemini-cli/redis-monitor/sql')

# SPs to install on each secondary, in this order. The dispatcher depends on
# VR and VR_CLR, so it goes LAST to avoid "CREATE PROC that EXECs a
# not-yet-installed SP" warnings (CREATE PROC does NOT validate nested EXEC
# calls at create time, so order is mostly defensive).
SP_DEPLOY_ORDER = [
    'usp_GenerateSyncScript_VR_CLR.sql',
    'usp_GenerateSyncScript_VR.sql',
    'usp_GenerateSyncScript_VR_Dispatcher.sql',
    'usp_GetMissingRows_CLR.sql',
]

# The ClrColumnOverrides seed is a separate table+rows, not an SP. We always
# run it after the SPs to make sure CLR tables work after a fresh install.
SEED_CLR_OVERRIDES = True

# Optional: also deploy to the primary if it needs usp_GetMissingRows
# (the non-CLR diff SP that the primary runs in its 4-part-name path).
DEPLOY_TO_PRIMARY = True
PRIMARY_ONLY_SPS = ['usp_GetMissingRows.sql']

SP_NAME_FOR_FILE = {
    'usp_GenerateSyncScript_VR_Dispatcher.sql': 'usp_GenerateSyncScript_VR_Dispatcher',
    'usp_GenerateSyncScript_VR_CLR.sql':         'usp_GenerateSyncScript_VR_CLR',
    'usp_GenerateSyncScript_VR.sql':             'usp_GenerateSyncScript_VR',
    'usp_GetMissingRows_CLR.sql':                'usp_GetMissingRows_CLR',
    'usp_GetMissingRows.sql':                    'usp_GetMissingRows',
}

def conn(server):
    ip, port, user, pw, db = server
    s = (f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={ip},{port};DATABASE={db};"
         f"UID={user};PWD={pw};TrustServerCertificate=yes;Encrypt=yes;")
    return pyodbc.connect(s, timeout=30, autocommit=True)

def read_sql(name: str) -> str:
    p = SQL_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"SQL file not found: {p}")
    return p.read_text(encoding='utf-8')

def split_batches(sql: str):
    """Split a SQL file on GO batch separators (line-only, case-insensitive)."""
    batches = []
    current = []
    for line in sql.splitlines():
        if re.match(r'^\s*GO\s*$', line, re.IGNORECASE):
            if current:
                batches.append('\n'.join(current))
                current = []
        else:
            current.append(line)
    if current:
        batches.append('\n'.join(current))
    return [b for b in batches if b.strip()]

def apply_one_sp(server, sp_filename: str) -> str:
    """DROP IF EXISTS + re-CREATE a single SP file on the given server.

    Some SP files use CREATE PROCEDURE, others use ALTER PROCEDURE. We DROP
    first regardless, then run the file's batches. If the file uses ALTER
    (which would fail on a freshly-dropped object), we swap the leading
    `ALTER PROCEDURE` to `CREATE PROCEDURE` so the file's body becomes a
    valid CREATE statement.

    Returns the sp_name (for logging).
    """
    sp_name = SP_NAME_FOR_FILE[sp_filename]
    raw_sql = read_sql(sp_filename)
    # Normalize: if file starts with ALTER PROCEDURE for our sp_name, swap
    # to CREATE PROCEDURE. We only do this for the exact sp_name so we
    # don't accidentally rewrite nested ALTERs in the SP body.
    altered = re.sub(
        r'^\s*ALTER\s+PROCEDURE\s+\[?dbo\]?\.\[?' + re.escape(sp_name) + r'\]?',
        'CREATE PROCEDURE [dbo].[' + sp_name + ']',
        raw_sql,
        count=1,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    batches = split_batches(altered)
    c = conn(server)
    cur = c.cursor()
    try:
        # DROP first, so the file's CREATE PROCEDURE succeeds even on re-runs
        # or if the body has changed.
        cur.execute(f'IF OBJECT_ID(\'dbo.{sp_name}\') IS NOT NULL DROP PROCEDURE dbo.{sp_name}')
        for i, b in enumerate(batches, 1):
            cur.execute(b)
        # Verify
        cur.execute("SELECT OBJECT_ID('dbo.' + ?) AS id", sp_name)
        r = cur.fetchone()
        if not r or not r[0]:
            raise RuntimeError(f'{sp_name} install reported success but OBJECT_ID is NULL')
    finally:
        c.close()
    return sp_name

def ensure_clr_overrides_seed(server):
    """Create ClrColumnOverrides table if missing, seed Farms overrides."""
    c = conn(server)
    cur = c.cursor()
    cur.execute('''
    IF OBJECT_ID('dbo.ClrColumnOverrides') IS NULL
    BEGIN
        CREATE TABLE dbo.ClrColumnOverrides (
            table_name  NVARCHAR(256) NOT NULL,
            column_name NVARCHAR(256) NOT NULL,
            cast_as     NVARCHAR(64)  NOT NULL DEFAULT 'NVARCHAR(MAX)',
            notes       NVARCHAR(500) NULL,
            updated_at  DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
            PRIMARY KEY (table_name, column_name)
        );
    END
    ''')
    for col in ('GeoPoint', 'FarmLatitude', 'FarmLongitude'):
        cur.execute('''
        IF NOT EXISTS (
            SELECT 1 FROM dbo.ClrColumnOverrides
            WHERE table_name = 'Farms' AND column_name = ?
        )
            INSERT INTO dbo.ClrColumnOverrides (table_name, column_name, cast_as, notes)
            VALUES ('Farms', ?, 'NVARCHAR(MAX)', 'auto-seeded for OPENQUERY pass-through');
        ''', (col, col))
    cur.execute("SELECT table_name, column_name, cast_as FROM dbo.ClrColumnOverrides ORDER BY table_name, column_name")
    rows = cur.fetchall()
    c.close()
    return rows

def main():
    print('Installing sync SPs on PROD secondaries (DROP+CREATE pattern, idempotent)', flush=True)

    for sec in PROD_SECONDARIES:
        print(f'\n=== PROD SEC {sec[0]}:{sec[1]} ===', flush=True)
        for fname in SP_DEPLOY_ORDER:
            try:
                sp = apply_one_sp(sec, fname)
                print(f'  [OK]   re-installed dbo.{sp}', flush=True)
            except Exception as e:
                print(f'  [FAIL] {fname}: {e}', flush=True)
                raise
        # Seed ClrColumnOverrides
        rows = ensure_clr_overrides_seed(sec)
        print(f'  ClrColumnOverrides seed: {len(rows)} row(s)', flush=True)
        for r in rows:
            print(f'    {r[0]}.{r[1]} -> {r[2]}', flush=True)

    if DEPLOY_TO_PRIMARY:
        print(f'\n=== PROD PRIMARY {PROD_PRIMARY[0]}:{PROD_PRIMARY[1]} ===', flush=True)
        for fname in PRIMARY_ONLY_SPS:
            try:
                sp = apply_one_sp(PROD_PRIMARY, fname)
                print(f'  [OK]   re-installed dbo.{sp}', flush=True)
            except Exception as e:
                print(f'  [FAIL] {fname}: {e}', flush=True)
                raise
        # Make sure ClrColumnOverrides table exists on primary too
        # (the updated usp_GetMissingRows will create it on first call,
        # but pre-creating is cleaner).
        c = conn(PROD_PRIMARY); cur = c.cursor()
        cur.execute('''
        IF OBJECT_ID('dbo.ClrColumnOverrides') IS NULL
        BEGIN
            CREATE TABLE dbo.ClrColumnOverrides (
                table_name  NVARCHAR(256) NOT NULL,
                column_name NVARCHAR(256) NOT NULL,
                cast_as     NVARCHAR(64)  NOT NULL DEFAULT 'NVARCHAR(MAX)',
                notes       NVARCHAR(500) NULL,
                updated_at  DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
                PRIMARY KEY (table_name, column_name)
            );
        END
        ''')
        c.close()
        print(f'  ClrColumnOverrides table ensured on primary', flush=True)

    print('\n=== Final summary: re-check all PROD secondaries ===', flush=True)
    final_check_sps = [
        'usp_GenerateSyncScript_VR_Dispatcher',
        'usp_GenerateSyncScript_VR',
        'usp_GenerateSyncScript_VR_CLR',
        'usp_GetMissingRows_CLR',
    ]
    all_ok = True
    for sec in PROD_SECONDARIES:
        c = conn(sec)
        cur = c.cursor()
        print(f'\n  PROD SEC {sec[0]}:', flush=True)
        for sp in final_check_sps:
            cur.execute("SELECT OBJECT_ID('dbo.' + ?) AS id", sp)
            r = cur.fetchone()
            mark = 'OK ' if (r and r[0]) else 'MISSING'
            if not (r and r[0]):
                all_ok = False
            print(f'    [{mark}] dbo.{sp}', flush=True)
        c.close()

    print('\n=== Done ===', flush=True)
    if all_ok:
        print('All PROD secondaries have the required sync SPs.', flush=True)
    else:
        print('!!! Some SPs are still missing. Check the output above.', flush=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
