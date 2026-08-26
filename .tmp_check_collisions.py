"""
Investigate the 9 User collisions on 10.10.98.100.

For each failing (Id, UserName) pair from the previous sync, look at
the secondary's row with that UserName — its Id will be different from
the primary's Id. We want to see if the secondary's row is older / newer
than the primary's, which would tell us whether this is:
  (a) a re-created user (primary got a new Id for the same UserName),
  (b) a sync that left a stale row on the secondary,
  (c) a different kind of divergence.

We avoid the pyodbc-problematic columns (datetimeoffset LockoutEnd at
col 12) by casting them away in the read query.
"""
import pyodbc

PRI = ('10.10.98.47', '1433', 'sa', 't5!bT5AZ5Q@coqZ', 'NitaraDB')
SEC = ('10.10.98.100', '1433', 'sa', 'P@ssw0rd@123', 'NitaraDB')

FAILING_PAIRS = [
    ('06488c7d-308d-4339-8000-01872156d887', '9606310180'),
    ('18f08378-e314-48cc-a3bd-47c5a6e9c225', '7899305339'),
    ('19896d13-e3fd-4b9f-96be-82c3ae5f7f6c', '9902550629'),
    ('74cef2b7-de7b-4c4d-9877-49f67f06b0f9', '6383599873'),
    ('75156011-a33e-4f9c-b9e6-f0505ac6ee45', '7829457537'),
    ('84d9906b-eec1-49cd-a90a-14a87547cb2b', '8618848259'),
    ('b32e03db-cbdf-458c-a6a7-181e01a07d7b', '9663709119'),
    ('c277d9a4-802d-402e-919a-6a4c77c48955', '9861522303'),
    ('ca3808bd-2934-4b95-b9f4-f5a43b859cc0', '8217862260'),
]

def conn(server):
    ip, port, user, pw, db = server
    s = (f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={ip},{port};DATABASE={db};"
         f"UID={user};PWD={pw};TrustServerCertificate=yes;Encrypt=yes;")
    return pyodbc.connect(s, timeout=30, autocommit=True)

# CAST the problem columns to NVARCHAR(MAX) so pyodbc can fetch them.
def safe_select(server, where_clause, params=()):
    c = conn(server); cur = c.cursor()
    sql = f'''
    SELECT Id, UserName, EmailConfirmed, IsActive, CreatedBy,
           CAST(CreatedTimeStamp AS NVARCHAR(MAX)) AS CreatedTimeStamp,
           CAST(UpdatedTimeStamp AS NVARCHAR(MAX)) AS UpdatedTimeStamp
    FROM dbo.Users
    WHERE {where_clause}
    '''
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    c.close()
    return cols, rows

print(f'{"UserName":<14} {"PRIMARY Id":<40} {"PRIMARY CreatedTimeStamp":<30} {"SECONDARY Id":<40} {"SECONDARY CreatedTimeStamp":<30}', flush=True)
print('-' * 160, flush=True)

for pri_id, username in FAILING_PAIRS:
    # Primary row
    _, pri_rows = safe_select(PRI, 'Id = ?', (pri_id,))
    pri_row = pri_rows[0] if pri_rows else None
    # Secondary row with same UserName (any Id)
    _, sec_rows = safe_select(SEC, 'UserName = ?', (username,))
    sec_row = sec_rows[0] if sec_rows else None
    print(f'\nUserName={username}', flush=True)
    if pri_row:
        print(f'  PRIMARY   Id={pri_row[0]}  Created={pri_row[5]}  IsActive={pri_row[3]}', flush=True)
    else:
        print(f'  PRIMARY:   <not found>', flush=True)
    if sec_row:
        print(f'  SECONDARY Id={sec_row[0]}  Created={sec_row[5]}  IsActive={sec_row[3]}', flush=True)
    else:
        print(f'  SECONDARY: <not found>', flush=True)
