USE [NitaraDB]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- CLR-safe variant of usp_GenerateSyncScript_VR.
-- Used for tables that contain CLR-type columns (e.g. [dbo].[Farms].[GeoPoint] geography).
-- Uses OPENQUERY (a pass-through query) so the linked server evaluates the SELECT
-- and returns a plain result set — sidesteps SQL Server error 7325:
--   "Objects exposing columns with CLR types are not allowed in distributed queries."

CREATE PROCEDURE [dbo].[usp_GenerateSyncScript_VR_CLR]
    @TableName       NVARCHAR(256),
    @RemoteServerIP  NVARCHAR(128) = '10.10.98.47',
    @RemoteDatabase  NVARCHAR(128) = 'NitaraDB'
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ColumnList       NVARCHAR(MAX) = '';
    DECLARE @SelectColumnList NVARCHAR(MAX) = '';
    DECLARE @PKColumn         NVARCHAR(128);
    DECLARE @FullScript       NVARCHAR(MAX) = '';
    DECLARE @HasIdentity      BIT = 0;

    -- 1. Identify the Primary Key column for the NOT IN filter
    SELECT TOP 1 @PKColumn = c.name
    FROM sys.index_columns ic
    JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
    JOIN sys.indexes  i ON ic.object_id = i.object_id  AND ic.index_id  = i.index_id
    WHERE i.is_primary_key = 1
      AND OBJECT_NAME(ic.object_id) = @TableName;
    SET @PKColumn = ISNULL(@PKColumn, 'Id');

    -- 2. Build column lists, excluding computed / hidden / rowversion / generated columns.
    --    CLR columns ARE included — the OPENQUERY in step 3 handles them.
    SELECT
        @ColumnList       += '[' + c.name + '], ',
        @SelectColumnList += 'R.[' + c.name + '], ',
        @HasIdentity       = CASE WHEN c.is_identity = 1 THEN 1 ELSE @HasIdentity END
    FROM sys.columns c
    JOIN sys.tables t ON c.object_id = t.object_id
    WHERE t.name = @TableName
      AND c.is_computed = 0
      AND c.is_hidden   = 0
      AND c.system_type_id <> 189
      AND (c.generated_always_type IS NULL OR c.generated_always_type = 0)
    ORDER BY c.column_id;

    IF @ColumnList = ''
    BEGIN
        RAISERROR('Table [%s] not found or has no valid columns.', 16, 1, @TableName);
        RETURN;
    END

    SET @ColumnList       = LEFT(@ColumnList,       LEN(@ColumnList)       - 1);
    SET @SelectColumnList = LEFT(@SelectColumnList, LEN(@SelectColumnList) - 1);

    -- 3. Build the script. OPENQUERY executes the inner SELECT on PRIMARY and
    --    returns a plain result set (sidesteps SQL Server error 7325 for CLR types).
    --    The NOT IN filter goes in the OUTER WHERE — referencing the secondary's
    --    local [dbo].[Farms] — because OPENQUERY sub-queries are parsed in the
    --    caller's session, not the linked server's.
    SET @FullScript  = '-- Sync Script (CLR-safe via OPENQUERY) for ' + @TableName + CHAR(13) + CHAR(10);
    SET @FullScript += CHAR(13) + CHAR(10);

    IF @HasIdentity = 1
    BEGIN
        SET @FullScript += 'SET IDENTITY_INSERT [' + @TableName + '] ON;' + CHAR(13) + CHAR(10);
        SET @FullScript += CHAR(13) + CHAR(10);
    END

    SET @FullScript += 'INSERT INTO [' + @TableName + '] (' + @ColumnList + ')' + CHAR(13) + CHAR(10);
    SET @FullScript += 'SELECT ' + @SelectColumnList + CHAR(13) + CHAR(10);
    SET @FullScript += 'FROM OPENQUERY([' + @RemoteServerIP + '], ''' + CHAR(13) + CHAR(10);
    SET @FullScript += '    SELECT ' + @ColumnList + CHAR(13) + CHAR(10);
    SET @FullScript += '    FROM [' + @RemoteDatabase + '].[dbo].[' + @TableName + ']';
    SET @FullScript += ''') AS R' + CHAR(13) + CHAR(10);
    -- Outer NOT IN — runs on the secondary, references the local [dbo].[<TableName>].
    SET @FullScript += 'WHERE R.[' + @PKColumn + '] NOT IN (SELECT [' + @PKColumn + '] FROM [dbo].[' + @TableName + ']);' + CHAR(13) + CHAR(10);
    SET @FullScript += CHAR(13) + CHAR(10);

    IF @HasIdentity = 1
    BEGIN
        SET @FullScript += 'SET IDENTITY_INSERT [' + @TableName + '] OFF;' + CHAR(13) + CHAR(10);
    END

    -- 4. Return single row with proper line breaks
    SELECT @FullScript AS [SyncScript];
END
GO
