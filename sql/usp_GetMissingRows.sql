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

    -- 1. Identify the Primary Key column for the JOIN logic
    SELECT TOP 1 @PKColumn = c.name
    FROM sys.index_columns ic
    JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
    JOIN sys.indexes i ON ic.object_id = i.object_id AND ic.index_id = i.index_id
    WHERE i.is_primary_key = 1
      AND OBJECT_NAME(ic.object_id) = @TableName;

    -- Fallback to 'Id' if no PK is defined
    SET @PKColumn = ISNULL(@PKColumn, 'Id');

    -- 2. Build column list (C#-aligned: exclude computed, hidden, rowversion, temporal generated)
    SELECT
        @ColumnList += 'R.[' + c.name + '], '
    FROM sys.columns c
    JOIN sys.tables t ON c.object_id = t.object_id
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
