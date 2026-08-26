USE [NitaraDB]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[usp_GetMissingRows]
    @TableName NVARCHAR(256),
    @SecondaryServerIP NVARCHAR(128),
    @SecondaryDatabase NVARCHAR(128) = 'NitaraDB'
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ColumnList NVARCHAR(MAX) = '';
    DECLARE @PKColumn NVARCHAR(128);

    -- 0. Make sure dbo.ClrColumnOverrides exists. The CLR SP and the diff
    --    SP both honor this table; the CLR SP deploys it on the secondary,
    --    the diff SP runs on the primary. CREATE IF NOT EXISTS makes the
    --    diff SP self-sufficient on first run.
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

    -- 1. Identify the Primary Key column for the JOIN logic
    SELECT TOP 1 @PKColumn = c.name
    FROM sys.index_columns ic
    JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
    JOIN sys.indexes i ON ic.object_id = i.object_id AND ic.index_id = i.index_id
    WHERE i.is_primary_key = 1
      AND OBJECT_NAME(ic.object_id) = @TableName;
    SET @PKColumn = ISNULL(@PKColumn, 'Id');

    -- 2. Build column list. Honor dbo.ClrColumnOverrides so columns whose
    --    ODBC type pyodbc can't fetch (datetimeoffset / datetime2 / time /
    --    geography / geometry / hierarchyid / sql_variant / xml) are CAST
    --    to NVARCHAR(MAX) (or whatever the override says) in the SELECT
    --    we send to the secondary. SQL Server can implicitly convert the
    --    resulting string back to the destination type on INSERT.
    --
    --    Note the alias is just `[col]` — NOT `R.[col]`. A `R.[col]` alias
    --    is parsed as a qualified table/column reference, not a column
    --    alias, and trips the parser with "Incorrect syntax near '.'".
    --
    --    C#-aligned column list: skip computed, hidden, rowversion (189),
    --    and generated-always columns.
    SELECT
        @ColumnList += CASE
            WHEN o.cast_as IS NOT NULL
                THEN 'CAST(R.[' + c.name + '] AS ' + o.cast_as + ') AS [' + c.name + '], '
            ELSE 'R.[' + c.name + '], '
        END
    FROM sys.columns c
    JOIN sys.tables t ON c.object_id = t.object_id
    LEFT JOIN dbo.ClrColumnOverrides o
        ON o.table_name  = @TableName
       AND o.column_name = c.name
    WHERE t.name = @TableName
      AND c.is_computed = 0
      AND c.is_hidden = 0
      AND c.system_type_id <> 189
      AND (c.generated_always_type IS NULL OR c.generated_always_type = 0)
    ORDER BY c.column_id;

    IF @ColumnList = ''
    BEGIN
        RAISERROR('Table [%s] not found or has no valid columns.', 16, 1, @TableName);
        RETURN;
    END

    -- Clean trailing comma
    SET @ColumnList = LEFT(@ColumnList, LEN(@ColumnList) - 1);

    -- 3. Query primary (local) rows that don't exist on secondary (linked server)
    DECLARE @sql NVARCHAR(MAX);
    SET @sql = 'SELECT ' + @ColumnList + '
        FROM dbo.[' + @TableName + '] AS R
        LEFT JOIN [' + @SecondaryServerIP + '].[' + @SecondaryDatabase + '].dbo.[' + @TableName + '] AS L
            ON R.[' + @PKColumn + '] = L.[' + @PKColumn + ']
        WHERE L.[' + @PKColumn + '] IS NULL;';

    EXEC sp_executesql @sql;
END
GO
