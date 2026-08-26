USE [NitaraDB]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- Returns the rows that exist on PRIMARY but are missing on SECONDARY,
-- for tables that have CLR-type columns (e.g. [dbo].[Farms].[GeoPoint] geography).
--
-- Runs on SECONDARY (which has a linked server pointing to PRIMARY).
-- Uses a SINGLE OPENQUERY against the primary, sidestepping SQL Server
-- error 7325 (CLR types can't be read via 4-part-name distributed queries).
--
-- === Why this was rewritten ===
-- The previous version chunked local PKs into 100-row NOT IN lists, emitted
-- one result set per chunk via sp_executesql in a WHILE loop, and relied on
-- the caller (pyodbc) to call nextset() to see them all. Two problems:
--   (1) The chunked logic was mathematically wrong: unioning "primary rows
--       NOT IN (chunk_i)" across all chunks gives almost all primary rows,
--       not "primary rows NOT IN (all local PKs)". For Farms, the result
--       was ~26817 "missing" rows that were actually already in local.
--   (2) pyodbc's fetchall() on a multi-result-set SP returns only the
--       FIRST result set, so callers (sync code) saw the wrong diff and
--       published thousands of false-positive "change" events to Kafka.
--
-- The fix: do the NOT IN ONCE on the secondary side (outside OPENQUERY).
-- The OPENQUERY inner string is just a column list of the primary table
-- (fixed size, ~few KB) and the NOT IN is evaluated locally — no 8000-char
-- limit on the inner string, and the SP returns a single result set with
-- the real diff.
--
-- Columns listed in dbo.ClrColumnOverrides are CAST to their override type
-- (e.g. NVARCHAR(MAX)) inside the OPENQUERY — same CLR-pass-through behavior
-- as the original (geography/geometry/hierarchyid, plus any NVARCHAR columns
-- whose values look numeric and would otherwise get coerced to float by
-- the ODBC driver).
--
-- Expected companion table (created separately):
--   CREATE TABLE dbo.ClrColumnOverrides (
--       table_name  NVARCHAR(256) NOT NULL,
--       column_name NVARCHAR(256) NOT NULL,
--       cast_as     NVARCHAR(64)  NOT NULL DEFAULT 'NVARCHAR(MAX)',
--       PRIMARY KEY (table_name, column_name)
--   );

CREATE PROCEDURE [dbo].[usp_GetMissingRows_CLR]
    @TableName          NVARCHAR(256),
    @PrimaryServerName  NVARCHAR(128),   -- e.g. '10.10.98.47' (must be a configured linked server on the secondary)
    @PrimaryDatabase    NVARCHAR(128) = 'NitaraDB'
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @InnerColList NVARCHAR(MAX) = '';  -- columns inside the OPENQUERY (with CAST overrides)
    DECLARE @OuterColList NVARCHAR(MAX) = '';  -- columns returned to the caller
    DECLARE @PKColumn     NVARCHAR(128);

    -- 0. PK discovery
    SELECT TOP 1 @PKColumn = c.name
    FROM sys.index_columns ic
    JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
    JOIN sys.indexes  i ON ic.object_id = i.object_id  AND ic.index_id  = i.index_id
    WHERE i.is_primary_key = 1
      AND OBJECT_NAME(ic.object_id) = @TableName;
    SET @PKColumn = ISNULL(@PKColumn, 'Id');

    -- 1. Build column lists. Only CAST columns that have an entry in
    --    dbo.ClrColumnOverrides (per-table, per-column). Everything else
    --    passes through as-is. Includes ALL columns (CLR + non-CLR).
    SELECT
        @OuterColList += '[' + c.name + '], ',
        @InnerColList += CASE
            WHEN o.cast_as IS NOT NULL
                THEN 'CAST([' + c.name + N'] AS ' + o.cast_as + N') AS [' + c.name + '], '
            ELSE '[' + c.name + N'] AS [' + c.name + '], '
        END
    FROM sys.columns c
    JOIN sys.tables t  ON c.object_id = t.object_id
    LEFT JOIN dbo.ClrColumnOverrides o
        ON o.table_name  = @TableName
       AND o.column_name = c.name
    WHERE t.name = @TableName
      AND c.is_computed = 0
      AND c.is_hidden   = 0
      AND c.system_type_id <> 189
      AND (c.generated_always_type IS NULL OR c.generated_always_type = 0)
    ORDER BY c.column_id;

    IF @OuterColList = ''
    BEGIN
        RAISERROR('Table [%s] not found or has no valid columns.', 16, 1, @TableName);
        RETURN;
    END

    SET @OuterColList = LEFT(@OuterColList, LEN(@OuterColList) - 1);
    SET @InnerColList = LEFT(@InnerColList, LEN(@InnerColList) - 1);

    -- 2. Single OPENQUERY (no chunking). The NOT IN runs on the SECONDARY
    --    (caller's session), not inside the remote pass-through, so:
    --      - no 8000-char limit on the inner string (it's just the column list)
    --      - one result set, not 270 — pyodbc fetchall() sees the real diff
    DECLARE @Sql NVARCHAR(MAX);
    SET @Sql = N'SELECT ' + @OuterColList + N' ' +
               N'FROM OPENQUERY([' + @PrimaryServerName + N'], ' +
                   CHAR(39) +
                       N'SELECT ' + @InnerColList + N' ' +
                       N'FROM [' + @PrimaryDatabase + N'].[dbo].[' + @TableName + N']' +
                   CHAR(39) +
               N') AS R ' +
               N'WHERE R.[' + @PKColumn + N'] NOT IN ' +
                   N'(SELECT [' + @PKColumn + N'] FROM [dbo].[' + @TableName + N']);';

    EXEC sp_executesql @Sql;
END
GO
