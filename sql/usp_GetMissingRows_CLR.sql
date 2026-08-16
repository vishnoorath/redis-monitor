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
-- Uses OPENQUERY against the primary, sidestepping SQL Server error 7325.
--
-- Columns listed in dbo.ClrColumnOverrides are CAST to their override type
-- (e.g. NVARCHAR(MAX)) before being returned — this handles two cases:
--   1. CLR types like geography / geometry / hierarchyid that ODBC can't carry
--   2. nvarchar columns whose values look numeric (e.g. '20.9425972') and get
--      mis-coerced to float by the ODBC driver
--
-- All OTHER columns pass through unchanged (their native types travel fine).
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

    DECLARE @OuterColList NVARCHAR(MAX) = '';  -- columns returned to the caller
    DECLARE @InnerColList NVARCHAR(MAX) = '';  -- columns inside the OPENQUERY (CAST only overrides)
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

    -- 2. Pull PKs from local table into a temp table via dynamic SQL
    CREATE TABLE #LocalPks (PkVal NVARCHAR(450) NOT NULL);

    DECLARE @PullSql NVARCHAR(MAX) =
        N'INSERT INTO #LocalPks (PkVal) ' +
        N'SELECT CAST([' + @PKColumn + N'] AS NVARCHAR(450)) ' +
        N'FROM [dbo].[' + @TableName + N'] ' +
        N'OPTION (MAXDOP 1);';
    EXEC sp_executesql @PullSql;

    DECLARE @LocalPkCount INT = (SELECT COUNT(*) FROM #LocalPks);
    DECLARE @Done INT = 0;
    DECLARE @LocalPkList NVARCHAR(MAX);

    -- 3. Process PKs in chunks so the OPENQUERY inner string stays under 8000 chars.
    WHILE @Done < @LocalPkCount
    BEGIN
        DECLARE @ChunkSize INT = 150;  -- ~150 PKs per chunk; tuned to keep OPENQUERY inner string safely under the 8KB limit

        SET @LocalPkList =
            STUFF(
                (
                    SELECT ',' + CHAR(39) + CHAR(39)
                                  + REPLACE(PkVal, CHAR(39), CHAR(39) + CHAR(39))
                                  + CHAR(39) + CHAR(39)
                    FROM (
                        SELECT PkVal
                        FROM #LocalPks
                        ORDER BY PkVal
                        OFFSET @Done ROWS FETCH NEXT @ChunkSize ROWS ONLY
                    ) AS chunk
                    FOR XML PATH(''), TYPE
                ).value('.', 'NVARCHAR(MAX)'),
                1, 1, '');

        IF @LocalPkList IS NULL OR LEN(@LocalPkList) = 0
            SET @LocalPkList = CHAR(39) + CHAR(39) + '__NO_LOCAL_PK__' + CHAR(39) + CHAR(39);

        DECLARE @WhereClause NVARCHAR(MAX) =
            N'WHERE [' + @PKColumn + N'] NOT IN (' + @LocalPkList + N')';

        DECLARE @InnerSql NVARCHAR(MAX);
        SET @InnerSql = N'SELECT ' + @InnerColList + N' ' +
                        N'FROM [' + @PrimaryDatabase + N'].[dbo].[' + @TableName + N'] ' +
                        @WhereClause;

        DECLARE @Sql NVARCHAR(MAX);
        SET @Sql = N'SELECT ' + @OuterColList + N' ' +
                   N'FROM OPENQUERY([' + @PrimaryServerName + N'], ' +
                   CHAR(39) + @InnerSql + CHAR(39) +
                   N') AS R;';

        EXEC sp_executesql @Sql;

        SET @Done = @Done + @ChunkSize;
    END

    DROP TABLE #LocalPks;
END
GO
