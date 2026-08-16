USE [NitaraDB]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- Single entry point that picks CLR-safe vs standard sync script generation.
-- Python calls this instead of usp_GenerateSyncScript_VR directly.
--   - If the table has any CLR-type column → usp_GenerateSyncScript_VR_CLR (OPENQUERY)
--   - Otherwise                            → usp_GenerateSyncScript_VR     (4-part-name LEFT JOIN)

CREATE PROCEDURE [dbo].[usp_GenerateSyncScript_VR_Dispatcher]
    @TableName       NVARCHAR(256),
    @RemoteServerIP  NVARCHAR(128) = '10.10.98.47',
    @RemoteDatabase  NVARCHAR(128) = 'NitaraDB'
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ClrCount INT = 0;
    SELECT @ClrCount = COUNT(*)
    FROM sys.columns c
    JOIN sys.tables t ON c.object_id = t.object_id
    JOIN sys.types  ty ON c.user_type_id = ty.user_type_id
    WHERE t.name = @TableName
      AND c.is_computed = 0
      AND c.is_hidden   = 0
      AND ty.is_assembly_type = 1
      AND (c.generated_always_type IS NULL OR c.generated_always_type = 0);

    IF @ClrCount > 0
        EXEC [dbo].[usp_GenerateSyncScript_VR_CLR]
             @TableName      = @TableName,
             @RemoteServerIP = @RemoteServerIP,
             @RemoteDatabase = @RemoteDatabase;
    ELSE
        EXEC [dbo].[usp_GenerateSyncScript_VR]
             @TableName      = @TableName,
             @RemoteServerIP = @RemoteServerIP,
             @RemoteDatabase = @RemoteDatabase;
END
GO
