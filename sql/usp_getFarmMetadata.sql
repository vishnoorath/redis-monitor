USE [NitaraDB]
GO
/****** Object:  StoredProcedure [dbo].[sp_get_FarmMetaData]    Script Date: 02-03-2026 19:00:48 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO



-- 00004_CreateOrAlter_sp_get_FarmMetaData.sql

-- CR DETAILS
-- Task 46912: Create Idempotent Scripts for changes made with 'GetFarmMetaDataSummary' and 'FarmMetaData' SPs

-- Author: Anant Singh Chauhan
-- Date: Dec 30, 2024 
-- Description: Adding idempotent script for already updated 'sp_get_FarmMetaData' SP by Murugan.


-- =============================================
-- Author:      Murugan Andezuthu Dharmaratnam
-- Create Date: 2024
-- Description: Get Cattle Meta Data 
-- Revision Dat / Comments:
-- =============================================

--Call SP
--exec [dbo].[sp_get_FarmMetaData] '42f27fbb-9c22-4e7e-b8a3-e11a495fdea6', 'Shed1', 'All', 100, 200,0,0,0  
ALTER PROCEDURE [dbo].[sp_get_FarmMetaData]
(
	@pFarmId nvarchar(256),
	@pDefaultShedName nvarchar(512),
	@pDefaultGroupName nvarchar(512),
	@pAppSettingsMaxlactationDaysForEarlyCount int,
	@pAppSettingsMaxlactationDaysForMidCount int,
	@pApplicationSettingsMorningSession nvarchar(256),
	@pApplicationSettingsAfternoonSession nvarchar(256),
	@pApplicationSettingsEveningSession nvarchar(256)
)
AS
BEGIN
    -- SET NOCOUNT ON added to prevent extra result sets from
    -- interfering with SELECT statements.
    SET NOCOUNT ON

	declare @pCattleIds [tt_string]
	insert into @pCattleIds([Name]) select CattleId from CattleContracts where FarmId = @pFarmId

	-- Update Current Status
	exec Update_CurrentStatus_New @pCattleIds

	Declare @Id Varchar(50)
	select @Id = Id from [dbo].[DefaultUsers] where IsActive = 'true'

	--insert into #CattleIds select [Name] from @pCattleIds

	declare @BreedId nvarchar(256) 
	declare @TreatmentId nvarchar(256)

	--Declare @UpcomingACtivity Table(
	--Id VarChar(50),CattleId VarChar(50),Activity VarChar(50),CalvingDate DateTime2,UpcomingActivityDate DateTime2,DependentDate DateTime2,ActivityCount bit
	--)
	-- INSERT INTO @UpcomingACtivity (Id,CattleId,Activity,CalvingDate,UpcomingActivityDate,DependentDate,ActivityCount)
	--EXEC [dbo].[USP_Get_UpcomingActivityDate] @pCattleIds; 

	--Declare @UpcomingACtivity Table(
	--Id VarChar(50),CattleId VarChar(50),Activity VarChar(50),DependentDate DateTime2,UpcomingActivityDate DateTime2
	--)
	--INSERT INTO @UpcomingACtivity (Id,CattleId,Activity,DependentDate,UpcomingActivityDate)
	--EXEC [dbo].USP_Get_UpcomingActivityDate_NewLogic @pCattleIds; 

	---- Check if the temporary table already exists and drop it if it does
	--IF OBJECT_ID('tempdb..#Treatment') IS NOT NULL
	--	DROP TABLE #Treatment;
	--select * into #Treatment  from (values ('9f3e5cfa-b79f-4c1e-b51f-890dbd2c86e8'),('cef7a7bf-7880-4363-ae77-22a4769d2c90'),('ded986ca-650d-420b-bfe6-c4f59794e10d')) as Treatment(Id)
		--IF OBJECT_ID('tempdb..#RegisteredBy') IS NOT NULL
		--DROP TABLE #RegisteredBy;
		
	DECLARE @RegisteredBy AS TABLE(CreatedBy NVARCHAR(50),RegisteredBy NVARCHAR(50))

	INSERT INTO @RegisteredBy
	SELECT DISTINCT c.CreatedBy, 
		CASE 
			WHEN EXISTS (
				SELECT 1 
				FROM [UserRoles] ur 
				JOIN [Roles] r ON ur.RoleId = r.Id 
				WHERE ur.UserId = c.CreatedBy 
				  AND r.RoleName NOT IN ('FARMER')
			) 
			THEN CONCAT(u.FirstName, ' ', ISNULL(u.MiddleName + ' ', ''), ISNULL(u.LastName, ''))
			ELSE NULL
		END AS RegisteredBy
	--INTO #RegisteredBy
	FROM [Cattles] c
	LEFT JOIN [Users] u ON u.Id = c.CreatedBy
	WHERE c.Id IN (SELECT [Name] FROM @pCattleIds);
	IF OBJECT_ID('tempdb..#CategoryTempTable') IS NOT NULL
		DROP TABLE #CategoryTempTable;

	--Create a temporary table to store the output
	CREATE TABLE #CategoryTempTable (
		CattleId NVARCHAR(50),
		Category NVARCHAR(50)
	);

	--Insert the results of the stored procedure execution into the temporary table
	INSERT INTO #CategoryTempTable (CattleId, Category)
	EXEC [dbo].[sp_get_CattleCategory] @pCattleIds;


	SELECT 
	[dbo].[Farms].Id, [dbo].[Farms].NitaraFarmId, [dbo].[Farms].FarmName, [dbo].[Farms].FarmLocation, [dbo].[Farms].FarmPinCode, [dbo].[Farms].IsActive, [dbo].[Farms].CreatedBy, [dbo].[Farms].CreatedTimeStamp, [dbo].[Farms].UpdatedBy, [dbo].[Farms].UpdatedTimeStamp, [dbo].[Farms].FarmLocationAlias, 
	-- [dbo].[Farms].FarmLatitude, [dbo].[Farms].FarmLongitude,
	(CASE WHEN FarmLatitude ='' THEN NULL ELSE [dbo].[Farms].FarmLatitude END ) as FarmLatitude,
	(CASE WHEN FarmLongitude ='' THEN NULL ELSE [dbo].[Farms].FarmLongitude  END ) as  FarmLongitude,	
	[dbo].[Farms].FarmTimeZone, [dbo].[Farms].State, [dbo].[Farms].Country, [dbo].[Farms].AdministrativeArea, [dbo].[Farms].Locality, [dbo].[Farms].AddressComponent, [dbo].[Farms].SubAdministrativeArea, [dbo].[Farms].SubLocality, [dbo].[Farms].AddressLine1, [dbo].[Farms].AddressLine2, [dbo].[Farms].AlternativeLocalityName, [dbo].[Farms].FarmPostOffice, [dbo].[Farms].LocationSource,
	(CASE WHEN FarmLatitude ='' THEN NULL ELSE CAST([dbo].[Farms].FarmLatitude as decimal(19,16)) END ) as Latitude,
	(CASE WHEN FarmLongitude ='' THEN NULL ELSE CAST([dbo].[Farms].FarmLongitude as decimal(19,16)) END ) as  Longitude,
	[dbo].[Farms].Id as farmId,	CAST(FarmTimeZone as int) as UtcOffsetInMins,
	[dbo].[Users].CountryCode as farmOwnerCountryCode, [dbo].[Users].ProfilePicPath as FarmOwnerProfilePicPath, [dbo].[Users].PhoneNumber as farmOwnerPhoneNumber, [dbo].[Users].Id as farmOwnerId, [dbo].[Users].FirstName as farmOwnerName, [dbo].[Users].ProfilePicPath as FarmOwnerProfilePicPath,
	(Select Top 1 ISNULL(iSactive,0)  from FarmProfile FP Where FP.FarmId= [dbo].[Farms].Id) AS IsFarmInfraAvailable
	FROM [dbo].[Farms]
	INNER JOIN [UserFarmContracts] ON [dbo].[UserFarmContracts].FarmId = [dbo].[Farms].Id
	inner join [dbo].[Users] on [dbo].[Users].Id = [dbo].[UserFarmContracts].UserId
	WHERE [dbo].[UserFarmContracts].FarmRole = 'Owner' AND [dbo].[Farms].[Id] = @pFarmId


	SELECT [Cattles].[Id] as CattleId, [Cattles].[Id], [Cattles].[BreedId], [Cattles].[Category], [Cattles].[CreatedBy], [Cattles].[CreatedTimeStamp] as CreatedDate, [Cattles].[CurrentStage] as CurrentStatus, [Cattles].[DamId], [Cattles].[DayOfBirth], [Cattles].[Gender], [Cattles].[IsActive], [Cattles].[InActiveTimeStamp], [Cattles].[LactationCount], [Cattles].[MonthOfBirth], [Cattles].[SireId], [Cattles].[TagNumber], [Cattles].[TypeOfCattle] as CattleType, [Cattles].[UpdatedBy], [Cattles].[UpdatedTimeStamp], [Cattles].[YearOfBirth], [Cattles].[CategoryUpdatedDate], [Cattles].[ReasonForDeletion], [Cattles].[Remarks], [Cattles].[Valuation],
	(
        SELECT TOP 1
            CASE 
                WHEN [Cattles].TypeOfCattle = 'Cattle_Cow' THEN DATEADD(DAY, 283, [Insemination].InseminationDateTime)
                WHEN [Cattles].TypeOfCattle = 'Cattle_Buffalo' THEN DATEADD(DAY, 309, [Insemination].InseminationDateTime)
            END
        FROM [BreedCycle]
        LEFT JOIN [tbl_Insemination] [Insemination] ON [Insemination].BreedCycleId = [BreedCycle].Id
        LEFT JOIN [tbl_Pd] [Pd] ON [Pd].BreedCycleId = [BreedCycle].Id
        WHERE [BreedCycle].CattleId = [Cattles].Id
          AND [Cattles].LactationCount = [BreedCycle].LactationNumber
          AND [Insemination].IsActive = 1
          AND [Pd].IsActive = 1
          AND [Pd].IsLatest = 1
    ) as ExpectedCalvingDate,
	(select top(1) ProfilePicturePath from [ProfilePicture] where [ProfilePicture].CattleId1 = [Cattles].[Id]) as FrontCattleProfilePics, 
	(select top(1) ProfilePicturePath from [ProfilePicture] where [ProfilePicture].CattleId2 = [Cattles].[Id]) as SideCattleProfilePics, 
	(select top(1) ProfilePicturePath from [ProfilePicture] where [ProfilePicture].CattleId = [Cattles].[Id]) as BodyCattleProfilePics, 
	(select top(1)  MajorBreed from [dbo].[Breed] where Id = [Cattles].[BreedId]) as Breed, 
	(select top(1) Category from #CategoryTempTable where #CategoryTempTable.CattleId = [Cattles].[Id]) as CattleCategory,
		rb.RegisteredBy,ContractType ,ContractDate,ContractWith,  CAST(Coalesce(ContractRate,0.00) AS decimal(10,2)) AS ContractRate,ContractRemarks,CattleUniqueId
		FROM [Cattles] 
		LEFT JOIN @RegisteredBy rb ON rb.CreatedBy = [Cattles].CreatedBy
		INNER JOIN CattleContracts CC ON [Cattles].Id = CC.CattleId
		WHERE [Cattles].[Id] IN (SELECT [Name] FROM @pCattleIds);
	



--SELECT [t].[Id], [t].[Cost], [t].[CreatedBy], [t].[CreatedTimeStamp], [t].[DateOfVisit], [t].[FollowupAnalysis], [t].[FollowupDate], [t].[IsActive], [t].[IsAntibioticGiven], [t].[MedicationNotes], [t].[NextFollowupRequired], [t].[Remarks], [t].[TreatmentFollowUpBy], [t].[TreatmentFollowUpByName], [t].[TreatmentId], [t].[TreatmentProofPath], [t].[UpdatedBy], [t].[UpdatedTimeStamp]
--FROM [TreatmentFollowup] AS [t]
--WHERE [t].[TreatmentId] in (select Id from #Treatment)

--SELECT [t].[Id], [t].[Cost], [t].[CreatedBy], [t].[CreatedTimeStamp], [t].[DateOfVisit], [t].[FollowupAnalysis], [t].[FollowupDate], [t].[IsActive], [t].[IsAntibioticGiven], [t].[MedicationNotes], [t].[NextFollowupRequired], [t].[Remarks], [t].[TreatmentFollowUpBy], [t].[TreatmentFollowUpByName], [t].[TreatmentId], [t].[TreatmentProofPath], [t].[UpdatedBy], [t].[UpdatedTimeStamp]
--FROM [TreatmentFollowup] AS [t]
--WHERE [t].[TreatmentId] in (select Id from #Treatment)

--SELECT [t].[Id], [t].[Cost], [t].[CreatedBy], [t].[CreatedTimeStamp], [t].[DateOfVisit], [t].[FollowupAnalysis], [t].[FollowupDate], [t].[IsActive], [t].[IsAntibioticGiven], [t].[MedicationNotes], [t].[NextFollowupRequired], [t].[Remarks], [t].[TreatmentFollowUpBy], [t].[TreatmentFollowUpByName], [t].[TreatmentId], [t].[TreatmentProofPath], [t].[UpdatedBy], [t].[UpdatedTimeStamp]
--FROM [TreatmentFollowup] AS [t]
--WHERE [t].[TreatmentId] in (select Id from #Treatment)

--SELECT [BreedCycle].[Id], [BreedCycle].[CalvingId], [BreedCycle].[CattleId], [BreedCycle].[CreatedBy], [BreedCycle].[CreatedTimeStamp], [BreedCycle].[DateOfDryPeriod], [BreedCycle].[IsActive], [BreedCycle].[LactationNumber], [BreedCycle].[LactationStartDate], [BreedCycle].[UpdatedBy], [BreedCycle].[UpdatedTimeStamp]
--FROM [BreedCycle]
--WHERE [BreedCycle].[CattleId]  in (select [Name] from @pCattleIds)

	SELECT [dbo].[tbl_Treatment].CattleId,[ActivityImageProofs].[Id], [ActivityImageProofs].[ActivityId], [ActivityImageProofs].[ActivityImageProofPath], [ActivityImageProofs].[ActivityType], [ActivityImageProofs].[CreatedBy], [ActivityImageProofs].[CreatedTimeStamp], [ActivityImageProofs].[IsActive], [ActivityImageProofs].[UpdatedBy], [ActivityImageProofs].[UpdatedTimeStamp]
	FROM [ActivityImageProofs]
	--INNER JOIN [dbo].[TreatmentFollowup] on [dbo].[TreatmentFollowup].Id = [ActivityImageProofs].ActivityId
	--INNER JOIN [dbo].[Treatment] on [dbo].[Treatment].Id = [dbo].[TreatmentFollowup].TreatmentId
	INNER JOIN [dbo].[tbl_Treatment]  on [dbo].[tbl_Treatment].TreatmentGuid = [dbo].[ActivityImageProofs].ActivityId
	INNER JOIN [dbo].[Cattles] on [dbo].[Cattles].Id = [dbo].[tbl_Treatment].CattleId
	WHERE [ActivityImageProofs].IsActive = 'true' 
	AND [dbo].[tbl_Treatment].[CattleId]  in (select [Name] from @pCattleIds)

	SELECT [dbo].[tbl_Treatment].CattleId,[ActivityImageProofs].[Id], [ActivityImageProofs].[ActivityId], [ActivityImageProofs].[ActivityImageProofPath], [ActivityImageProofs].[ActivityType], [ActivityImageProofs].[CreatedBy], [ActivityImageProofs].[CreatedTimeStamp], [ActivityImageProofs].[IsActive], [ActivityImageProofs].[UpdatedBy], [ActivityImageProofs].[UpdatedTimeStamp]
	FROM [ActivityImageProofs]
	INNER JOIN [dbo].[tbl_Treatment]  on [dbo].[tbl_Treatment].TreatmentGuid = [dbo].[ActivityImageProofs].ActivityId
	INNER JOIN [dbo].[Cattles] on [dbo].[Cattles].Id = [dbo].[tbl_Treatment].CattleId
	WHERE [ActivityImageProofs].IsActive = 'true'
	AND [dbo].[tbl_Treatment].[CattleId]  in (select [Name] from @pCattleIds)

	SELECT [dbo].[tbl_Deworming].CattleId,[ActivityImageProofs].[Id], [ActivityImageProofs].[ActivityId], [ActivityImageProofs].[ActivityImageProofPath], [ActivityImageProofs].[ActivityType], [ActivityImageProofs].[CreatedBy], [ActivityImageProofs].[CreatedTimeStamp], [ActivityImageProofs].[IsActive], [ActivityImageProofs].[UpdatedBy], [ActivityImageProofs].[UpdatedTimeStamp]
	FROM [ActivityImageProofs]
	INNER JOIN [dbo].[tbl_Deworming] on [dbo].[tbl_Deworming].DewormingGuid = [ActivityImageProofs].ActivityId
	INNER JOIN [dbo].[Cattles] on [dbo].[Cattles].Id = [dbo].[tbl_Deworming].CattleId
	WHERE [ActivityImageProofs].IsActive = 'true'
	AND [dbo].[tbl_Deworming].[CattleId]  in (select [Name] from @pCattleIds)

	SELECT [dbo].[tbl_Vaccination].CattleId,[ActivityImageProofs].[Id], [ActivityImageProofs].[ActivityId], [ActivityImageProofs].[ActivityImageProofPath], [ActivityImageProofs].[ActivityType], [ActivityImageProofs].[CreatedBy], [ActivityImageProofs].[CreatedTimeStamp], [ActivityImageProofs].[IsActive], [ActivityImageProofs].[UpdatedBy], [ActivityImageProofs].[UpdatedTimeStamp]
	FROM [ActivityImageProofs]
	INNER JOIN [dbo].[tbl_Vaccination] on [dbo].[tbl_Vaccination].VaccinationGuid = [ActivityImageProofs].ActivityId
	INNER JOIN [dbo].[Cattles] on [dbo].[Cattles].Id = [dbo].[tbl_Vaccination].CattleId
	WHERE [ActivityImageProofs].IsActive = 'true' AND  [ActivityImageProofs].[ActivityImageProofPath] IS NOT NULL
	AND [dbo].[tbl_Vaccination].[CattleId]  in (select [Name] from @pCattleIds)

	--SELECT [dbo].[tbl_CattleGrooming].CattleId,[ActivityImageProofs].[Id], [ActivityImageProofs].[ActivityId], [ActivityImageProofs].[ActivityImageProofPath], [ActivityImageProofs].[ActivityType], [ActivityImageProofs].[CreatedBy], [ActivityImageProofs].[CreatedTimeStamp], [ActivityImageProofs].[IsActive], [ActivityImageProofs].[UpdatedBy], [ActivityImageProofs].[UpdatedTimeStamp]
	--FROM [ActivityImageProofs]
	--INNER JOIN [dbo].[tbl_CattleGrooming] on [dbo].[tbl_CattleGrooming].CattleGroomingGuid = [ActivityImageProofs].ActivityId
	--INNER JOIN [dbo].[Cattles] on [dbo].[Cattles].Id = [dbo].[tbl_CattleGrooming].CattleId
	--WHERE [ActivityImageProofs].IsActive = 'true'
	--AND [dbo].[tbl_CattleGrooming].[CattleId]  in (select [Name] from @pCattleIds)

	SELECT [tbl_BcsLog].BcsLogGuid AS [Id], [tbl_BcsLog].[BcsScore], [tbl_BcsLog].[CattleId], [tbl_BcsLog].[CreatedBy], [tbl_BcsLog].[CreatedTimeStamp], [tbl_BcsLog].[DateOfBcs], [tbl_BcsLog].[IsActive], [tbl_BcsLog].[Length], [tbl_BcsLog].[UpdatedBy], [tbl_BcsLog].[UpdatedTimeStamp]
	FROM [tbl_BcsLog]
	WHERE [tbl_BcsLog].[CattleId]  in (select [Name] from @pCattleIds)

	SELECT [BreedCycle].Id, [BreedCycle].LactationNumber, [BreedCycle].LactationStartDate, [BreedCycle].DateOfDryPeriod, [BreedCycle].CalvingGuid as CalvingId, [BreedCycle].IsActive, [BreedCycle].CreatedBy, [BreedCycle].CreatedTimeStamp, [BreedCycle].UpdatedBy, [BreedCycle].UpdatedTimeStamp, [BreedCycle].CattleId,[BreedCycle].IsBreedingDetailsUpdated
	FROM [dbo].[BreedCycle]
	WHERE [BreedCycle].[CattleId]  in (select [Name] from @pCattleIds)

	--Calving
	--SELECT [Calving].Id, [Calving].CalvingDateTime, [Calving].CalvingBy, [Calving].Colostrum, [Calving].IsActive, [Calving].CreatedBy, [Calving].CreatedTimeStamp, [Calving].UpdatedBy, [Calving].UpdatedTimeStamp, [Calving].PreviousRecordedActivity, [Calving].PreviousRecordedActivityId, [Calving].Dystocia, [Calving].PlacentaExpelledTime, [Calving].IsManualIntervention, [Calving].ManualInterventionReportedBy, [Calving].ManualInterventionReportedDetails, [Calving].RopNotificationTimeStamp, [Calving].RopNotificationCount, [Calving].CalvingByName
	--FROM [Calving]
	--INNER JOIN [BreedCycle] ON [BreedCycle].CalvingId = [Calving].Id
	--WHERE [BreedCycle].[CattleId]  in (select [Name] from @pCattleIds)
	-- Execute the provided queries
		-- Query 1: Calving
		SELECT C.CalvingGuid as Id, C.CalvingDateTime, C.CalvingBy, C.Colostrum, 
			   C.IsActive, C.CreatedBy, C.CreatedTimeStamp, C.UpdatedBy, 
			   C.UpdatedTimeStamp, C.PreviousRecordedActivity, C.PreviousRecordedActivityId, 
			   C.Dystocia, C.PlacentaExpelledTime, C.IsManualIntervention, 
			   C.ManualInterventionReportedBy, C.ManualInterventionReportedDetails, 
			   C.RopNotificationTimeStamp, C.RopNotificationCount, C.CalvingByName ,C.OrganizationId
			  ,C.PerformedFor,C.PerformedForName,C.PerformedBy,C.RecordStatus,C.RecordStatusDate,C.RecordStatusRemarks,C.ReasonCode
		FROM [tbl_Calving] as C
		INNER JOIN [BreedCycle] ON [BreedCycle].calvingGuid = [C].calvingGuid
		WHERE [BreedCycle].[CattleId] IN (SELECT [Name] FROM @pCattleIds);

	--Heat
	--SELECT [Heat].Id, [Heat].HeatDate, [Heat].HeatType, [Heat].IsActive, [Heat].CreatedBy, [Heat].CreatedTimeStamp, [Heat].UpdatedBy, [Heat].UpdatedTimeStamp, [Heat].BreedCycleId, [Heat].PreviousRecordedActivity, [Heat].IsLatest, [Heat].PreviousRecordedActivityId
	--FROM [Heat]
	--INNER JOIN [BreedCycle] ON [BreedCycle].Id = [Heat].BreedCycleId
	--WHERE [BreedCycle].[CattleId]  in (select [Name] from @pCattleIds)
		SELECT H.HeatGuid as Id, H.HeatDate, H.HeatType, H.IsActive, H.CreatedBy, 
			   H.CreatedTimeStamp, H.UpdatedBy, H.UpdatedTimeStamp, H.BreedCycleId, 
			   H.PreviousRecordedActivity, H.IsLatest, H.PreviousRecordedActivityId,H.OrganizationId
			  ,H.PerformedFor,H.PerformedForName,H.PerformedBy,H.RecordStatus,H.RecordStatusDate,H.RecordStatusRemarks,H.ReasonCode,H.IsAutoRecorded
		FROM [tbl_Heat] as H
		INNER JOIN [BreedCycle] ON [BreedCycle].Id = H.BreedCycleId
		WHERE [BreedCycle].[CattleId] IN (SELECT [Name] FROM @pCattleIds);

	--Insemination
	--SELECT [Insemination].Id, [Insemination].InseminationDateTime, [Insemination].InseminatedBy, [Insemination].IsSuccessful, [Insemination].IsActive, [Insemination].CreatedBy, [Insemination].CreatedTimeStamp, [Insemination].UpdatedBy, [Insemination].UpdatedTimeStamp, [Insemination].BreedCycleId, [Insemination].PreviousRecordedActivity, [Insemination].IsLatest, [Insemination].PreviousRecordedActivityId, [Insemination].InseminationNumber, [Insemination].InseminatedByName
	--FROM [Insemination]
	--INNER JOIN [BreedCycle] ON [BreedCycle].Id = [Insemination].BreedCycleId
	--WHERE [BreedCycle].[CattleId]  in (select [Name] from @pCattleIds)
			SELECT I.InseminationGuid as Id, I.InseminationDateTime, I.InseminatedBy, 
			   I.IsSuccessful, I.IsActive, I.CreatedBy, 
			   I.CreatedTimeStamp, I.UpdatedBy, I.UpdatedTimeStamp, 
			   I.BreedCycleId, I.PreviousRecordedActivity, I.IsLatest, 
			   I.PreviousRecordedActivityId, I.InseminationNumber, I.InseminatedByName,I.OrganizationId
			  ,I.PerformedFor,I.PerformedForName,I.PerformedBy,I.RecordStatus,I.RecordStatusDate,I.RecordStatusRemarks,I.ReasonCode
		FROM [tbl_Insemination] as I
		INNER JOIN [BreedCycle] ON [BreedCycle].Id = I.BreedCycleId
		WHERE [BreedCycle].[CattleId] IN (SELECT [Name] FROM @pCattleIds);

	--InseminationType
	--SELECT [InseminationType].Id, [InseminationType].Type, [InseminationType].SemenBrand, [InseminationType].BullId, [InseminationType].StrawPicturePath, [InseminationType].BreedCode, [InseminationType].SemenStation, [InseminationType].EjaculationNumber, [InseminationType].GeoLocationOfService, [InseminationType].Comment, [InseminationType].IsActive, [InseminationType].CreatedBy, [InseminationType].CreatedTimeStamp, [InseminationType].UpdatedBy, [InseminationType].UpdatedTimeStamp, [InseminationType].InseminationId, [InseminationType].DateOfProduction, [InseminationType].MonthOfYear, [InseminationType].[DayOfYear], [InseminationType].StrawPictureTimeStamp
	--FROM [InseminationType]
	--INNER JOIN [Insemination] ON [Insemination].Id = [InseminationType].InseminationId
	--INNER JOIN [BreedCycle] ON [BreedCycle].Id = [Insemination].BreedCycleId
	--WHERE [BreedCycle].[CattleId]  in (select [Name] from @pCattleIds)
		SELECT IT.InseminationTypeGuid as Id, IT.Type, IT.SemenBrand, 
			   IT.BullId, IT.StrawPicturePath, IT.BreedCode, 
			   IT.SemenStation, IT.EjaculationNumber, IT.GeoLocationOfService, 
			   IT.Comment, IT.IsActive, IT.CreatedBy, 
			   IT.CreatedTimeStamp, IT.UpdatedBy, IT.UpdatedTimeStamp, 
			   IT.InseminationGuid as InseminationId, IT.DateOfProduction, IT.MonthOfYear, 
			   IT.[DayOfYear], IT.StrawPictureTimeStamp
		FROM [tbl_InseminationType] as IT
		INNER JOIN tbL_Insemination I ON I.InseminationGuid = IT.InseminationGuid
		INNER JOIN [BreedCycle] ON [BreedCycle].Id = I.BreedCycleId
		WHERE [BreedCycle].[CattleId] IN (SELECT [Name] FROM @pCattleIds);

	--Pd
	--SELECT [Pd].Id, [Pd].PdDateTime, [Pd].PdResult, [Pd].PdBy, [Pd].PdProcess, [Pd].IsActive, [Pd].CreatedBy, [Pd].CreatedTimeStamp, [Pd].UpdatedBy, [Pd].UpdatedTimeStamp, [Pd].BreedCycleId, [Pd].PreviousRecordedActivity, [Pd].IsLatest, [Pd].PreviousRecordedActivityId, [Pd].PdByName
	--FROM [Pd]
	--INNER JOIN [BreedCycle] ON [BreedCycle].Id = [Pd].BreedCycleId
	--WHERE [BreedCycle].[CattleId]  in (select [Name] from @pCattleIds)
			SELECT [Pd].PdGuid as Id, [Pd].PdDateTime, [Pd].PdResult, [Pd].PdBy, [Pd].PdProcess, [Pd].IsActive, 
			   [Pd].CreatedBy, [Pd].CreatedTimeStamp, [Pd].UpdatedBy, [Pd].UpdatedTimeStamp, [Pd].BreedCycleId, 
			   [Pd].PreviousRecordedActivity, [Pd].IsLatest, [Pd].PreviousRecordedActivityId, [Pd].PdByName,[Pd].OrganizationId
			  ,[Pd].PerformedFor,[Pd].PerformedForName,[Pd].PerformedBy,[Pd].RecordStatus,[Pd].RecordStatusDate,[Pd].RecordStatusRemarks,[Pd].ReasonCode,[Pd].IsAutoRecorded
		FROM [tbl_Pd] as Pd
		INNER JOIN [BreedCycle] ON [BreedCycle].Id = [Pd].BreedCycleId
		WHERE [BreedCycle].[CattleId] IN (SELECT [Name] FROM @pCattleIds);

	--CalvingResult
	--SELECT [CalvingResult].[Id], [CalvingResult].[CalfType], [CalvingResult].[CalvingDateTime], [CalvingResult].[CalvingId], [CalvingResult].[CattleId], [CalvingResult].[CattleLactationNumber], [CalvingResult].[CreatedBy], [CalvingResult].[CreatedTimeStamp], [CalvingResult].[IsActive], [CalvingResult].[LifeStatus], [CalvingResult].[UpdatedBy], [CalvingResult].[UpdatedTimeStamp]
	--FROM [CalvingResult]
	--WHERE [CalvingResult].[CattleId]  in (select [Name] from @pCattleIds)
			SELECT CR.CalvingResultGuid as Id, CR.[CalfType], CR.[CalvingDateTime], 
			   CR.[CalvingGuid] AS [CalvingId], CR.[CattleId], CR.[CattleLactationNumber], 
			   CR.[CreatedBy], CR.[CreatedTimeStamp], CR.[IsActive], 
			   CR.[LifeStatus], CR.[UpdatedBy], CR.[UpdatedTimeStamp]
		FROM [tbl_CalvingResult] as CR
		WHERE CR.[CattleId] IN (SELECT [Name] FROM @pCattleIds);


	SELECT [CattleContracts].[Id], [CattleContracts].[CattleId], [CattleContracts].[CreatedBy], [CattleContracts].[CreatedTimeStamp], [CattleContracts].[FarmId], [CattleContracts].[FarmOwnerId], [CattleContracts].[IsActive], [CattleContracts].[PurchaseDate], [CattleContracts].[SoldDate], [CattleContracts].[UpdatedBy], [CattleContracts].[UpdatedTimeStamp]
	FROM [CattleContracts]
	WHERE [CattleContracts].[CattleId] in (select [Name] from @pCattleIds)

	SELECT [CooperativeNumber].Id, [CooperativeNumber].Number, [CooperativeNumber].IsActive, [CooperativeNumber].CreatedBy, [CooperativeNumber].CreatedTimeStamp, [CooperativeNumber].UpdatedBy, [CooperativeNumber].UpdatedTimeStamp, [CooperativeNumber].CattleId
	FROM [CooperativeNumber]
	WHERE [CooperativeNumber].[IsActive] = 'true'
	AND [CooperativeNumber].[CattleId]  in (select [Name] from @pCattleIds)

	select [dbo].[Cattles].Id as CattleId, * from [dbo].[Dam]
	INNER JOIN [dbo].[Cattles] ON [dbo].[Cattles].DamId = [dbo].[Dam].Id
	where [dbo].[Cattles].Id in (select [Name] from @pCattleIds)

	SELECT [tbl_Deworming].DewormingGuid AS [Id], [tbl_Deworming].ConsultationFee AS[Amount], [tbl_Deworming].[BrandName], [tbl_Deworming].[CattleId], [tbl_Deworming].DewormingCost AS [Cost], [tbl_Deworming].[CreatedBy], [tbl_Deworming].CreatedDateTime AS [CreatedTimeStamp], [tbl_Deworming].DewormingDateTime AS [DewormingDate], [tbl_Deworming].[DewormingProofFilePath], [tbl_Deworming].[IsActive], [tbl_Deworming].[ProcessedBy], [tbl_Deworming].[ProcessedByName], [tbl_Deworming].[UpdatedBy], [tbl_Deworming].UpdatedDateTime AS [UpdatedTimeStamp],[tbl_Deworming].BatchGuid
	FROM [tbl_Deworming]
	WHERE [tbl_Deworming].[IsActive] = 'true'
	AND [tbl_Deworming].[CattleId]  in (select [Name] from @pCattleIds)

	SELECT [tbl_DewormerType].DewormerTypeGuid AS Id, [tbl_DewormerType].Type,[tbl_DewormerType].CombinationSaltName,[tbl_DewormerType].IsCombinationSalt, [tbl_DewormerType].IsActive, [tbl_DewormerType].CreatedBy, [tbl_DewormerType].CreatedDateTime AS CreatedTimeStamp, [tbl_DewormerType].UpdatedBy, [tbl_DewormerType].UpdatedDateTime AS UpdatedTimeStamp, [tbl_DewormerType].DewormingGuid AS DewormingId
	from [dbo].[tbl_DewormerType] 
	INNER JOIN [tbl_Deworming] on [tbl_Deworming].DewormingId =  [dbo].[tbl_DewormerType].DewormingId
	INNER JOIN [dbo].[Cattles] on [dbo].[Cattles].Id = [tbl_Deworming].CattleId
	WHERE [tbl_Deworming].[IsActive] = 'true'
	AND [tbl_Deworming].[CattleId]  in (select [Name] from @pCattleIds)


    SELECT [tbl_CattleGrooming].CattleGroomingGuid AS [Id], [tbl_CattleGrooming].ConsultationFee AS[Amount], [tbl_CattleGrooming].[CattleId], [tbl_CattleGrooming].GroomingTypeCode AS [GroomingTypeCode], [tbl_CattleGrooming].GroomingTypeOtherName AS [GroomingTypeOtherName], [tbl_CattleGrooming].GroomingMethodCode AS [GroomingMethodCode] , [tbl_CattleGrooming].[CreatedBy], [tbl_CattleGrooming].CreatedDateTime AS [CreatedTimeStamp], [tbl_CattleGrooming].GroomingDateTime AS [GroomingDate], [tbl_CattleGrooming].[IsActive], [tbl_CattleGrooming].PerformedBy, [tbl_CattleGrooming].UpdatedBy, [tbl_CattleGrooming].UpdatedDateTime AS [UpdatedTimeStamp],[tbl_CattleGrooming].BatchGuid
	FROM [tbl_CattleGrooming]
	WHERE [tbl_CattleGrooming].[IsActive] = 1
	AND [tbl_CattleGrooming].[CattleId]  in (select [Name] from @pCattleIds)

	-- Disease
	--SELECT [Disease].TreatmentDiseaseGuid AS [Id], [Disease].[CattleId], [Disease].[CreatedBy], [Disease].[CreatedTimeStamp], [Disease].[DiseaseCode] AS [DiseaseName], [Disease].[IsActive], [Disease].[TreatmentId], [Disease].[UpdatedBy], [Disease].[UpdatedTimeStamp]
	--FROM [tbl_TreatmentDisease] [Disease]
	--WHERE [Disease].[CattleId]  in (select [Name] from @pCattleIds)

	SELECT td.TreatmentDiseaseGuid AS Id, td.DiseaseCode AS DiseaseName, td.IsActive, td.CreatedBy, td.CreatedTimeStamp, td.UpdatedBy, td.UpdatedTimeStamp,  t.TreatmentGuid as TreatmentId, td.CattleId 
		FROM [tbl_TreatmentDisease] td 
		INNER JOIN [tbl_Treatment] t ON t.TreatmentId = td.TreatmentId WHERE t.CattleId IN (SELECT [Name] FROM @pCattleIds)
	

	--Symptom
	SELECT [Symptom].TreatmentSymptomGuid AS Id, [Symptom].SymptomCode AS SymptomName, [Symptom].IsActive, [Symptom].CreatedBy, [Symptom].CreatedTimeStamp, [Symptom].UpdatedBy, [Symptom].UpdatedTimeStamp, [Disease].DiseaseCode AS DiseaseId
	FROM [tbl_TreatmentSymptom] [Symptom]
	INNER JOIN [tbl_Treatment] [Treatment] ON [Treatment].TreatmentId = [Symptom].TreatmentId
	INNER JOIN [tbl_TreatmentDisease] [Disease] ON [Disease].TreatmentId = [Symptom].TreatmentId
	WHERE [Disease].[CattleId]  in (select [Name] from @pCattleIds)

	--SELECT [Disease].[Id], [Disease].[CattleId], [Disease].[CreatedBy], [Disease].[CreatedTimeStamp], [Disease].[DiseaseName], [Disease].[IsActive], [Disease].[TreatmentId], [Disease].[UpdatedBy], [Disease].[UpdatedTimeStamp]
	--FROM [Disease]
	--WHERE [Disease].[CattleId]  in (select [Name] from @pCattleIds)

	--SELECT [Symptom].Id, [Symptom].SymptomName, [Symptom].IsActive, [Symptom].CreatedBy, [Symptom].CreatedTimeStamp, [Symptom].UpdatedBy, [Symptom].UpdatedTimeStamp, [Symptom].DiseaseId
	--FROM [Symptom]
	--INNER JOIN [Disease] ON [Disease].Id = [Symptom].DiseaseId
	--WHERE [Disease].[CattleId]  in (select [Name] from @pCattleIds)

	select [dbo].[Cattles].Id as CattleId, * from [dbo].[Sire]
	INNER JOIN [dbo].[Cattles] ON [dbo].[Cattles].SireId = [dbo].[Sire].Id
	where [dbo].[Cattles].Id in (select [Name] from @pCattleIds)

	--SELECT [Treatment].[Id], [Treatment].[Amount], [Treatment].[CattleId], [Treatment].[CreatedBy], [Treatment].[CreatedTimeStamp], [Treatment].[DateOfVisit], [Treatment].[DiagnosisProofFilePath], [Treatment].[FollowupDays], [Treatment].[IsActive], [Treatment].[IsAntibioticGiven], [Treatment].[IsCured], [Treatment].[IsCuredTimeStamp], [Treatment].[IsFollowupRequired], [Treatment].[MedicationNotes], [Treatment].[TreatmentBy], [Treatment].[TreatmentByName], [Treatment].[TreatmentDetail], [Treatment].[TreatmentProofPath], [Treatment].[UpdatedBy], [Treatment].[UpdatedTimeStamp],[Treatment].[FollowupDate]
	--FROM [Treatment]
	--WHERE [Treatment].[CattleId]  in (select [Name] from @pCattleIds) ORDER BY UpdatedTimeStamp DESC

	--SELECT [Disease].Id, [Disease].DiseaseName, [Disease].IsActive, [Disease].CreatedBy, [Disease].CreatedTimeStamp, [Disease].UpdatedBy, [Disease].UpdatedTimeStamp, [Disease].TreatmentId, [Disease].CattleId
	--FROM [dbo].[Disease]
	--INNER JOIN [Treatment] ON [Treatment].Id = [Disease].TreatmentId
	--WHERE [Treatment].[CattleId]  in (select [Name] from @pCattleIds)

	--SELECT [Symptom].Id, [Symptom].SymptomName, [Symptom].IsActive, [Symptom].CreatedBy, [Symptom].CreatedTimeStamp, [Symptom].UpdatedBy, [Symptom].UpdatedTimeStamp, [Symptom].DiseaseId
	--FROM [Symptom]
	--INNER JOIN [Disease] ON [Disease].Id = [Symptom].DiseaseId
	--INNER JOIN [Treatment] ON [Treatment].Id = [Disease].TreatmentId
	--WHERE [Treatment].[CattleId]  in (select [Name] from @pCattleIds)

	--SELECT  [TreatmentFollowup].Id, [TreatmentFollowup].FollowupAnalysis, [TreatmentFollowup].TreatmentProofPath, [TreatmentFollowup].IsAntibioticGiven, [TreatmentFollowup].DateOfVisit, [TreatmentFollowup].FollowupDate, [TreatmentFollowup].NextFollowupRequired, [TreatmentFollowup].Remarks, [TreatmentFollowup].IsActive, [TreatmentFollowup].CreatedBy, [TreatmentFollowup].CreatedTimeStamp, [TreatmentFollowup].UpdatedBy, [TreatmentFollowup].UpdatedTimeStamp, [TreatmentFollowup].TreatmentId, [TreatmentFollowup].MedicationNotes, [TreatmentFollowup].Cost, [TreatmentFollowup].TreatmentFollowUpBy, [TreatmentFollowup].TreatmentFollowUpByName
	--FROM [TreatmentFollowup]
	--INNER JOIN [Treatment] ON [Treatment].Id = [TreatmentFollowup].TreatmentId
	--WHERE [Treatment].[CattleId]  in (select [Name] from @pCattleIds)

	--SELECT [MedicationDetail].Id, [MedicationDetail].Medicine, [MedicationDetail].Dosage, [MedicationDetail].Unit, [MedicationDetail].IsActive, [MedicationDetail].CreatedBy, [MedicationDetail].CreatedTimeStamp, [MedicationDetail].UpdatedBy, [MedicationDetail].UpdatedTimeStamp, [MedicationDetail].TreatmentFollowupId, [MedicationDetail].TreatmentId
	--FROM [MedicationDetail]
	--INNER JOIN [Treatment] ON [Treatment].Id = [MedicationDetail].TreatmentId
	--WHERE [Treatment].[CattleId]  in (select [Name] from @pCattleIds)

		--Treatement
				;WITH DefaultDisease AS (SELECT td.*, ROW_NUMBER() OVER (PARTITION BY td.TreatmentId ORDER BY td.CreatedTimeStamp desc) 
		AS RN FROM [tbl_TreatmentDisease] td) 
		SELECT t.TreatmentGuid AS Id, t.TreatmentCost AS Amount, t.CattleId, t.CreatedBy, t.CreatedTimeStamp, t.TreatmentDate AS DateOfVisit, null AS DiagnosisProofFilePath, dd.FollowupDays, t.IsActive, 
		null as IsAntibioticGiven, dd.IsCured, dd.CuredTimeStamp AS IsCuredTimeStamp, dd.IsNextFollowupRequired AS IsFollowupRequired, t.MedicationNotes, t.TreatmentBy, t.TreatmentByName, NULL AS TreatmentDetail, 
		null as TreatmentProofPath, t.UpdatedBy, t.UpdatedTimeStamp, dd.NextFollowupDate AS FollowupDate FROM [tbl_Treatment] t 
		LEFT JOIN DefaultDisease dd ON t.TreatmentId = dd.TreatmentId AND dd.RN = 1 WHERE t.CattleId IN (SELECT [Name] FROM @pCattleIds) ORDER BY t.UpdatedTimeStamp DESC

		
		---disease
		SELECT td.TreatmentDiseaseGuid AS Id, td.DiseaseCode AS DiseaseName, td.IsActive, td.CreatedBy, td.CreatedTimeStamp, td.UpdatedBy, td.UpdatedTimeStamp,  t.TreatmentGuid as TreatmentId, td.CattleId 
		FROM [tbl_TreatmentDisease] td 
		INNER JOIN [tbl_Treatment] t ON t.TreatmentId = td.TreatmentId WHERE t.CattleId IN (SELECT [Name] FROM @pCattleIds)
	
	----Symptom
				SELECT ts.TreatmentSymptomGuid AS Id, ts.SymptomCode AS SymptomName, ts.IsActive, ts.CreatedBy, ts.CreatedTimeStamp, ts.UpdatedBy, ts.UpdatedTimeStamp, td.TreatmentDiseaseGuid AS DiseaseId 
		FROM [tbl_TreatmentSymptom] ts INNER JOIN [tbl_TreatmentDisease] td ON ts.TreatmentId = td.TreatmentId 
		INNER JOIN [tbl_Treatment] t ON t.TreatmentId = ts.TreatmentId WHERE t.CattleId IN (SELECT [Name] FROM @pCattleIds)

	
		----TreatmentFollowup
		;WITH DefaultDisease AS (SELECT td.*, ROW_NUMBER() OVER (PARTITION BY td.TreatmentId ORDER BY td.CreatedTimeStamp desc) AS RN FROM [tbl_TreatmentDisease] td)
		SELECT dd.TreatmentDiseaseGuid AS Id, null as FollowupAnalysis, null as TreatmentProofPath, null as IsAntibioticGiven,
		t.TreatmentDate AS DateOfVisit, dd.NextFollowupDate AS FollowupDate, dd.IsNextFollowupRequired AS NextFollowupRequired, null as Remarks, dd.IsActive, 
		dd.CreatedBy, dd.CreatedTimeStamp, dd.UpdatedBy, dd.UpdatedTimeStamp, t.TreatmentGuid as TreatmentId, t.MedicationNotes, t.TreatmentCost AS Cost, t.TreatmentBy AS TreatmentFollowUpBy, 
		t.TreatmentByName AS TreatmentFollowUpByName FROM DefaultDisease dd 
		INNER JOIN [tbl_Treatment] t ON t.TreatmentId = dd.TreatmentId WHERE dd.RN = 1 AND t.CattleId IN (SELECT [Name] FROM @pCattleIds)

			----MedicationDetail
		;WITH DefaultMedication AS (SELECT tmd.*, ROW_NUMBER() OVER (PARTITION BY tmd.TreatmentId ORDER BY tmd.CreatedTimeStamp desc) AS RN 
		FROM [tbl_TreatmentMedicationDetail] tmd) 
		SELECT dm.TreatmentMedicationDetailGuid AS Id, dm.MedicineName AS Medicine, dm.Dosage, dm.Unit, dm.IsActive, dm.CreatedBy, dm.CreatedTimeStamp, dm.UpdatedBy, dm.UpdatedTimeStamp, 
		NULL AS TreatmentFollowupId, t.TreatmentGuid as TreatmentId FROM DefaultMedication dm 
		INNER JOIN [tbl_Treatment] t ON t.TreatmentId = dm.TreatmentId WHERE dm.RN = 1 AND t.CattleId IN (SELECT [Name] FROM @pCattleIds)


	--SELECT [UpcomingActivity].[Id], [UpcomingActivity].[Activity], [UpcomingActivity].[CattleId], [UpcomingActivity].[CreatedBy], [UpcomingActivity].[CreatedTimeStamp], [UpcomingActivity].[DependentDate], [UpcomingActivity].[IsActive], [UpcomingActivity].[LactationNumber], [UpcomingActivity].[LatestActivity], [UpcomingActivity].[UpdatedBy], [UpcomingActivity].[UpdatedTimeStamp],[UA].[UpcomingActivityDate]
	--FROM [UpcomingActivity]
	--INNER JOIN @UpcomingACtivity UA on [UA].[Id] = [UpcomingActivity].[CattleId]
	--WHERE [UpcomingActivity].[IsActive] = 'true'
	--AND [UpcomingActivity].[CattleId]  in (select [Name] from @pCattleIds)
	EXEC [dbo].USP_Get_UpcomingActivityDate_NewLogic @pCattleIds

	--SELECT [UpcomingHealthActivity].[Id], [UpcomingHealthActivity].[Activity], [UpcomingHealthActivity].[ActivityDate], [UpcomingHealthActivity].[ActivityDetail], [UpcomingHealthActivity].[CattleId], [UpcomingHealthActivity].[CreatedBy], [UpcomingHealthActivity].[CreatedTimeStamp], [UpcomingHealthActivity].[UpdatedBy], [UpcomingHealthActivity].[UpdatedTimeStamp]
	--FROM [UpcomingHealthActivity]
	--WHERE [UpcomingHealthActivity].[CattleId]  in (select [Name] from @pCattleIds)
	--EXEC Usp_Get_UpComingHealthActivityDate @pCattleIds
	EXEC Usp_Get_UpComingHealthActivityDate_NewLogic @pCattleIds

	SELECT [tbl_Vaccination].VaccinationGuid AS [Id], [tbl_Vaccination].[Amount], [tbl_Vaccination].[CattleId], [tbl_Vaccination].[Cost], [tbl_Vaccination].[CreatedBy], [tbl_Vaccination].[CreatedTimeStamp], [tbl_Vaccination].[Dosage], [tbl_Vaccination].[IsActive], [tbl_Vaccination].[Unit], [tbl_Vaccination].[UpdatedBy], [tbl_Vaccination].[UpdatedTimeStamp], [tbl_Vaccination].[VaccinatedBy], [tbl_Vaccination].[VaccinationBrand], [tbl_Vaccination].[VaccinationByName], [tbl_Vaccination].[VaccinationDateTime], [tbl_Vaccination].[VaccinationProofFilePath]
	FROM [tbl_Vaccination]
	WHERE [tbl_Vaccination].[IsActive] = 'true'
	AND [tbl_Vaccination].[CattleId]  in (select [Name] from @pCattleIds)

	SELECT [tbl_VaccinationType].VaccinationTypeGuid AS Id, [tbl_VaccinationType].Type, [tbl_VaccinationType].IsActive, [tbl_VaccinationType].CreatedBy, [tbl_VaccinationType].CreatedTimeStamp, [tbl_VaccinationType].UpdatedBy, [tbl_VaccinationType].UpdatedTimeStamp, [tbl_VaccinationType].VaccinationGuid AS VaccinationId 
	FROM [dbo].[tbl_VaccinationType]
	INNER JOIN [dbo].[tbl_Vaccination] ON [dbo].[tbl_Vaccination].VaccinationGuid = [dbo].[tbl_VaccinationType].VaccinationGuid
	INNER JOIN [dbo].[Cattles] on [dbo].[Cattles].Id = [tbl_Vaccination].CattleId
	WHERE 1=1
	--AND [Vaccination].[IsActive] = 'true'
	AND [tbl_Vaccination].[CattleId]  in (select [Name] from @pCattleIds)

	SELECT [tbl_WeightLog].WeightLogGuid AS[Id], [tbl_WeightLog].[CattleId], [tbl_WeightLog].[CreatedBy], [tbl_WeightLog].[CreatedTimeStamp], [tbl_WeightLog].[DateOfWeight], [tbl_WeightLog].[Girth], [tbl_WeightLog].[IsActive], [tbl_WeightLog].[Length], [tbl_WeightLog].[UpdatedBy], [tbl_WeightLog].[UpdatedTimeStamp], [tbl_WeightLog].[Weight]
	FROM [tbl_WeightLog]
	WHERE [tbl_WeightLog].[IsActive] = 'true'
	AND [tbl_WeightLog].[CattleId]  in (select [Name] from @pCattleIds)


	SELECT [tbl_CattleLabTests].CattleLabTestsGuid AS Id, [tbl_CattleLabTests].FarmId, [tbl_CattleLabTests].Age, [tbl_CattleLabTests].Gender, [tbl_CattleLabTests].TestName, [tbl_CattleLabTests].SampleType, NULL AS Comments, NULL AS Discipline, [tbl_CattleLabTests].LabTestDate AS TestRegistrationDate, [tbl_CattleLabTests].LabTestDate AS SampleCollectionDate, [tbl_CattleLabTests].LabTestDate AS SampleReceivedDate, [tbl_CattleLabTests].LabTestDate AS ReportDate, [tbl_CattleLabTests].IsActive, 
	CONCAT([dbo].[Users].FirstName,' ',[dbo].[Users].MiddleName,' ',[dbo].[Users].LastName) as CreatedBy, [tbl_CattleLabTests].CreatedTimeStamp, [tbl_CattleLabTests].UpdatedBy, [tbl_CattleLabTests].UpdatedTimeStamp, [tbl_CattleLabTests].CattleId,[tbl_CattleLabTests].TeatSequence,[tbl_CattleLabTests].TestResult
	FROM [tbl_CattleLabTests]
	INNER JOIN [dbo].[Users] ON [dbo].[Users].Id = [tbl_CattleLabTests].CreatedBy
	WHERE [tbl_CattleLabTests].TestName = 'CMT'
	AND [tbl_CattleLabTests].[CattleId]  in (select [Name] from @pCattleIds) AND [tbl_CattleLabTests].IsActive =1
	

	select [dbo].[Cattles].Id as CattleId, 
	COALESCE([dbo].[Cattles].CreatedBy,
	--(select Id from [dbo].[DefaultUsers] where IsActive = 'true')
	@Id) as NotificationReceiver,
	[dbo].[BreedingPreference].Id, [dbo].[BreedingPreference].Activity, [dbo].[BreedingPreference].IsNotificationOpted, [dbo].[BreedingPreference].DayOfFirstNotificationBeforeActivity, [dbo].[BreedingPreference].Interval, [dbo].[BreedingPreference].DependentProperty, [dbo].[BreedingPreference].DaysDifference, [dbo].[BreedingPreference].IsActive, [dbo].[BreedingPreference].CreatedBy, [dbo].[BreedingPreference].CreatedTimeStamp, [dbo].[BreedingPreference].UpdatedBy, [dbo].[BreedingPreference].UpdatedTimeStamp, [dbo].[BreedingPreference].PreferenceId, [dbo].[BreedingPreference].IsAppNotificationOpted, [dbo].[BreedingPreference].IsSMSNotificationOpted, [dbo].[BreedingPreference].IsWhatsAppNotificationOpted
	from [dbo].[BreedingPreference]
	inner join [dbo].[Cattles] ON COALESCE([dbo].[Cattles].CreatedBy,
	--(select Id from [dbo].[DefaultUsers] where IsActive = 'true')
	@Id) = [dbo].[BreedingPreference].CreatedBy
	where [dbo].[Cattles].Id  in (select [Name] from @pCattleIds)

	select [dbo].[Shed].*
	from [dbo].[Shed]
	where FarmId = @pFarmId and IsActive='true' and ShedName != @pDefaultShedName

	select [dbo].[Group].* 
	from [dbo].[Group]
	inner join [dbo].[Shed]  on [dbo].[Shed].Id = [dbo].[Group].ShedId
	where [dbo].[Shed].FarmId = @pFarmId
	and [dbo].[Shed].IsActive='true' 
	and [dbo].[Shed].ShedName != @pDefaultShedName
	and [dbo].[Group].IsActive = 'true'
	and [dbo].[Group].GroupName != @pDefaultGroupName

	--InBreedingBullIds
	DECLARE @pCattleId tt_string
	exec sp_get_AllParentBullIds @pCattleId

	exec sp_get_ViewFarmMilking @pFarmId, @pAppSettingsMaxlactationDaysForEarlyCount, @pAppSettingsMaxlactationDaysForMidCount

	--delete from @pCattleIds
	exec [dbo].[sp_get_GetDayWiseCattleMilkingData] @pCattleIds,@pApplicationSettingsMorningSession, @pApplicationSettingsAfternoonSession, @pApplicationSettingsEveningSession

	-- Abortion
	SELECT A.AbortionId,A.AbortionGuid,A.AbortionDateTime,A.AbortionReason,A.OtherReason,A.IsLatest,A.IsActive,A.CreatedBy,A.CreatedTimeStamp,A.UpdatedBy,A.UpdatedTimeStamp,
		   A.BreedCycleId, A.IsManualIntervention,A.ManualInterventionReportedby,A.ManualInterventionReportedDetails,A.RopNotificationTimeStamp,A.RopNotificationCount,
		   A.PlacentaExpelledTime
	FROM tbl_Abortion A INNER JOIN [BreedCycle] ON [BreedCycle].Id = BreedCycleId
	WHERE [BreedCycle].[CattleId] IN (SELECT [Name] FROM @pCattleIds);  
END
