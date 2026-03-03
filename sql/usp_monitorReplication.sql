CREATE PROCEDURE usp_GetTableCount_ForMonitoring_Replication
AS
BEGIN

-- Declare a table variable to hold table names
DECLARE @Tables TABLE (
    Id INT IDENTITY(1,1),
    TableName NVARCHAR(128)
);

-- Declare a table variable to store results (necessary for SELECT output)
DECLARE @Results TABLE (
    TableName NVARCHAR(128),
    RowCountEx BIGINT
);

-- Populate the table variable with table names from dbo schema
INSERT INTO @Tables (TableName)
SELECT QUOTENAME(t.name)
FROM sys.tables t
WHERE t.schema_id = SCHEMA_ID('dbo')
ORDER BY t.name;

-- Declare variables for the loop
DECLARE @MaxId INT = (SELECT MAX(Id) FROM @Tables);
DECLARE @CurrentId INT = 1;
DECLARE @TableName NVARCHAR(128);
DECLARE @SQL NVARCHAR(MAX);
DECLARE @RowCountEx BIGINT;

-- Loop through all tables
WHILE @CurrentId <= @MaxId
BEGIN
    -- Get the current table name
    SELECT @TableName = TableName
    FROM @Tables
    WHERE Id = @CurrentId;

    -- Dynamically generate the COUNT(*) statement
    SET @SQL = '
        SELECT @RowCountEx = COUNT(*)
        FROM dbo.' + @TableName;

    -- Execute the dynamic SQL and capture the row count
    EXEC sp_executesql 
        @SQL,
        N'@RowCountEx BIGINT OUTPUT',
        @RowCountEx OUTPUT;

    -- Insert the result into the results table variable
    INSERT INTO @Results (TableName, RowCountEx)
    VALUES (@TableName, @RowCountEx);

    -- Increment the counter
    SET @CurrentId = @CurrentId + 1;
END;

-- Output the results as a SELECT statement
SELECT 
    TableName,
    RowCountEx
FROM @Results
ORDER BY TableName;

END