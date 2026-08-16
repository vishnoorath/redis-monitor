USE [NitaraDB]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- Per-(table, column) override: tells usp_GetMissingRows_CLR which columns to
-- CAST when streaming them through OPENQUERY.
--
-- Only columns listed here get CAST. Everything else passes through unchanged.
--
-- Add a row whenever ODBC mis-translates a column (typical cases):
--   - CLR types (geography, geometry, hierarchyid, ...) — ODBC can't carry them
--   - nvarchar columns holding numeric-looking strings — ODBC auto-coerces to float
--
-- The Python settings page lets users manage rows here.

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
GO

-- Seed the columns that actually need casting for the currently tracked
-- change-tracking-enabled tables. If a row already exists (manually edited),
-- this is a no-op.
SET NOCOUNT ON;
IF NOT EXISTS (SELECT 1 FROM dbo.ClrColumnOverrides WHERE table_name='Farms' AND column_name='GeoPoint')
    INSERT INTO dbo.ClrColumnOverrides (table_name, column_name, cast_as, notes)
    VALUES ('Farms', 'GeoPoint', 'NVARCHAR(MAX)',
            '[dbo].[Farms].[GeoPoint] is geography (CLR) — ODBC cannot transport it natively.');

IF NOT EXISTS (SELECT 1 FROM dbo.ClrColumnOverrides WHERE table_name='Farms' AND column_name='FarmLatitude')
    INSERT INTO dbo.ClrColumnOverrides (table_name, column_name, cast_as, notes)
    VALUES ('Farms', 'FarmLatitude', 'NVARCHAR(MAX)',
            '[dbo].[Farms].[FarmLatitude] is nvarchar but stores numeric coords (e.g. ''20.9425972'') — ODBC auto-coerces to float and overflows.');

IF NOT EXISTS (SELECT 1 FROM dbo.ClrColumnOverrides WHERE table_name='Farms' AND column_name='FarmLongitude')
    INSERT INTO dbo.ClrColumnOverrides (table_name, column_name, cast_as, notes)
    VALUES ('Farms', 'FarmLongitude', 'NVARCHAR(MAX)',
            '[dbo].[Farms].[FarmLongitude] is nvarchar but stores numeric coords (e.g. ''70.6175452'') — ODBC auto-coerces to float and overflows.');
GO
