USE [NitaraDB]
GO

/****** Object:  StoredProcedure [dbo].[usp_GetRecentlyUpdatedFarmIds]    ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- =============================================
-- Author:      AI Assistant
-- Create Date: 2026-03-02
-- Description: Get list of Farm IDs updated/inserted in last N minutes
--              Checks all direct and indirect farm dependencies
-- Parameters:  @pMinutesBack INT = 30 (minutes to look back from now)
-- Returns:     DISTINCT list of FarmIds with recent activity
-- =============================================

CREATE PROCEDURE [dbo].[usp_GetRecentlyUpdatedFarmIds]
(
    @pMinutesBack INT = 30
)
AS
BEGIN
    SET NOCOUNT ON
    
    DECLARE @ThresholdTime DATETIME2 = DATEADD(MINUTE, -@pMinutesBack, GETUTCDATE())
    
    -- Main query combining all farm-dependent table changes
    -- Uses UNION to deduplicate FarmIds across different table sources
    
    SELECT DISTINCT FarmId
    FROM
    (
        -- ============================================
        -- LEVEL 0-1: Direct Farm Tables
        -- ============================================
        
        -- 1. Farms table direct updates
        SELECT DISTINCT f.Id AS FarmId
        FROM [dbo].[Farms] f
        WHERE f.CreatedTimeStamp >= @ThresholdTime 
           OR f.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 2. CattleContracts - links farms to cattle
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[CattleContracts] cc
        WHERE cc.CreatedTimeStamp >= @ThresholdTime 
           OR cc.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 3. UserFarmContracts - farm user/owner changes
        SELECT DISTINCT ufc.FarmId
        FROM [dbo].[UserFarmContracts] ufc
        WHERE ufc.CreatedTimeStamp >= @ThresholdTime 
           OR ufc.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 4. Shed - farm infrastructure
        SELECT DISTINCT s.FarmId
        FROM [dbo].[Shed] s
        WHERE s.CreatedTimeStamp >= @ThresholdTime 
           OR s.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 5. FarmProfile - farm profile updates
        SELECT DISTINCT fp.FarmId
        FROM [dbo].[FarmProfile] fp
        WHERE fp.CreatedTimeStamp >= @ThresholdTime 
           OR fp.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 6. tbl_CattleLabTests - lab tests on farms
        SELECT DISTINCT clt.FarmId
        FROM [dbo].[tbl_CattleLabTests] clt
        WHERE clt.CreatedTimeStamp >= @ThresholdTime 
           OR clt.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- ============================================
        -- LEVEL 2: Cattles via CattleContracts
        -- ============================================
        
        -- 7. Cattles - cattle records (join back to farm)
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[Cattles] c
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE c.CreatedTimeStamp >= @ThresholdTime 
           OR c.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 8. BreedCycle - breeding cycles
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[BreedCycle] bc
        INNER JOIN [dbo].[Cattles] c ON bc.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE bc.CreatedTimeStamp >= @ThresholdTime 
           OR bc.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- ============================================
        -- LEVEL 3: Breeding Activities via BreedCycle
        -- ============================================
        
        ---- 9. tbl_Calving - calving records
        --SELECT DISTINCT cc.FarmId
        --FROM [dbo].[tbl_Calving] cal
        --INNER JOIN [dbo].[BreedCycle] bc ON cal.BreedCycleId = bc.Id
        --INNER JOIN [dbo].[Cattles] c ON bc.CattleId = c.Id
        --INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        --WHERE cal.CreatedTimeStamp >= @ThresholdTime 
        --   OR cal.UpdatedTimeStamp >= @ThresholdTime
        
        --UNION
        
        ---- 10. tbl_CalvingResult - calving results
        --SELECT DISTINCT cc.FarmId
        --FROM [dbo].[tbl_CalvingResult] cr
        --INNER JOIN [dbo].[tbl_Calving] cal ON cr.CalvingId = cal.Id
        --INNER JOIN [dbo].[BreedCycle] bc ON cal.BreedCycleId = bc.Id
        --INNER JOIN [dbo].[Cattles] c ON bc.CattleId = c.Id
        --INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        --WHERE cr.CreatedTimeStamp >= @ThresholdTime 
        --   OR cr.UpdatedTimeStamp >= @ThresholdTime
        
        --UNION
        
        -- 11. tbl_Heat - heat cycles
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_Heat] h
        INNER JOIN [dbo].[BreedCycle] bc ON h.BreedCycleId = bc.Id
        INNER JOIN [dbo].[Cattles] c ON bc.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE h.CreatedTimeStamp >= @ThresholdTime 
           OR h.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 12. tbl_Insemination - insemination records
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_Insemination] ins
        INNER JOIN [dbo].[BreedCycle] bc ON ins.BreedCycleId = bc.Id
        INNER JOIN [dbo].[Cattles] c ON bc.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE ins.CreatedTimeStamp >= @ThresholdTime 
           OR ins.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 13. tbl_InseminationType - insemination type details
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_InseminationType] it
        INNER JOIN [dbo].[tbl_Insemination] ins ON it.InseminationId = ins.InseminationId
        INNER JOIN [dbo].[BreedCycle] bc ON ins.BreedCycleId = bc.Id
        INNER JOIN [dbo].[Cattles] c ON bc.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE it.CreatedTimeStamp >= @ThresholdTime 
           OR it.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 14. tbl_Pd - pregnancy detection
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_Pd] pd
        INNER JOIN [dbo].[BreedCycle] bc ON pd.BreedCycleId = bc.Id
        INNER JOIN [dbo].[Cattles] c ON bc.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE pd.CreatedTimeStamp >= @ThresholdTime 
           OR pd.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 15. tbl_Abortion - abortion records
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_Abortion] ab
        INNER JOIN [dbo].[BreedCycle] bc ON ab.BreedCycleId = bc.Id
        INNER JOIN [dbo].[Cattles] c ON bc.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE ab.CreatedTimeStamp >= @ThresholdTime 
           OR ab.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- ============================================
        -- LEVEL 3: Health/Treatment Activities via Cattles
        -- ============================================
        
        -- 16. tbl_Treatment - treatment records
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_Treatment] t
        INNER JOIN [dbo].[Cattles] c ON t.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE t.CreatedTimeStamp >= @ThresholdTime 
           OR t.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 17. tbl_TreatmentDisease - treatment disease mapping
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_TreatmentDisease] td
        INNER JOIN [dbo].[tbl_Treatment] t ON td.TreatmentId = t.TreatmentId
        INNER JOIN [dbo].[Cattles] c ON t.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE td.CreatedTimeStamp >= @ThresholdTime 
           OR td.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 18. tbl_TreatmentSymptom - treatment symptom mapping
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_TreatmentSymptom] ts
        INNER JOIN [dbo].[tbl_Treatment] t ON ts.TreatmentId = t.TreatmentId
        INNER JOIN [dbo].[Cattles] c ON t.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE ts.CreatedTimeStamp >= @ThresholdTime 
           OR ts.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 19. tbl_TreatmentMedicationDetail - treatment medication details
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_TreatmentMedicationDetail] tmd
        INNER JOIN [dbo].[tbl_Treatment] t ON tmd.TreatmentId = t.TreatmentId
        INNER JOIN [dbo].[Cattles] c ON t.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE tmd.CreatedTimeStamp >= @ThresholdTime 
           OR tmd.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 20. tbl_Deworming - deworming records
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_Deworming] dw
        INNER JOIN [dbo].[Cattles] c ON dw.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE dw.CreatedDateTime >= @ThresholdTime 
           OR dw.UpdatedDateTime >= @ThresholdTime
        
        UNION
        
        -- 21. tbl_DewormerType - dewormer type details
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_DewormerType] dwt
        INNER JOIN [dbo].[tbl_Deworming] dw ON dwt.DewormingId = dw.DewormingId
        INNER JOIN [dbo].[Cattles] c ON dw.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE dwt.CreatedDateTime >= @ThresholdTime 
           OR dwt.UpdatedDateTime >= @ThresholdTime
        
        UNION
        
        -- 22. tbl_Vaccination - vaccination records
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_Vaccination] vac
        INNER JOIN [dbo].[Cattles] c ON vac.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE vac.CreatedTimeStamp >= @ThresholdTime 
           OR vac.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 23. tbl_VaccinationType - vaccination type details
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_VaccinationType] vt
        INNER JOIN [dbo].[tbl_Vaccination] vac ON vt.VaccinationId = vac.VaccinationId
        INNER JOIN [dbo].[Cattles] c ON vac.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE vt.CreatedTimeStamp >= @ThresholdTime 
           OR vt.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 24. tbl_CattleGrooming - grooming records
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_CattleGrooming] cg
        INNER JOIN [dbo].[Cattles] c ON cg.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE cg.CreatedDateTime >= @ThresholdTime 
           OR cg.UpdatedDateTime >= @ThresholdTime
        
        UNION
        
        -- ============================================
        -- LEVEL 3: Measurements & Monitoring via Cattles
        -- ============================================
        
        -- 25. tbl_BcsLog - body condition score logs
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_BcsLog] bcs
        INNER JOIN [dbo].[Cattles] c ON bcs.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE bcs.CreatedTimeStamp >= @ThresholdTime 
           OR bcs.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 26. tbl_WeightLog - weight logs
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[tbl_WeightLog] wl
        INNER JOIN [dbo].[Cattles] c ON wl.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE wl.CreatedTimeStamp >= @ThresholdTime 
           OR wl.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        ---- 27. BreedingPreference - breeding preferences
        --SELECT DISTINCT cc.FarmId
        --FROM [dbo].[BreedingPreference] bp
        --INNER JOIN [dbo].[CattleContracts] cc ON bp.CattleId = cc.CattleId
        --WHERE bp.CreatedTimeStamp >= @ThresholdTime 
        --   OR bp.UpdatedTimeStamp >= @ThresholdTime
        
        -- UNION
        
        -- ============================================
        -- LEVEL 3: Activity Image Proofs via GUIDs
        -- ============================================
        
        -- 28. ActivityImageProofs - activity image proofs
        --     (covers Treatment, Deworming, Vaccination, Calving via GUID links)
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[ActivityImageProofs] aip
        INNER JOIN [dbo].[tbl_Treatment] t ON t.TreatmentGuid = aip.ActivityId
        INNER JOIN [dbo].[Cattles] c ON t.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE aip.CreatedTimeStamp >= @ThresholdTime 
           OR aip.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 29. ActivityImageProofs via Deworming
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[ActivityImageProofs] aip
        INNER JOIN [dbo].[tbl_Deworming] dw ON dw.DewormingGuid = aip.ActivityId
        INNER JOIN [dbo].[Cattles] c ON dw.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE aip.CreatedTimeStamp >= @ThresholdTime 
           OR aip.UpdatedTimeStamp >= @ThresholdTime
        
        UNION
        
        -- 30. ActivityImageProofs via Vaccination
        SELECT DISTINCT cc.FarmId
        FROM [dbo].[ActivityImageProofs] aip
        INNER JOIN [dbo].[tbl_Vaccination] vac ON vac.VaccinationGuid = aip.ActivityId
        INNER JOIN [dbo].[Cattles] c ON vac.CattleId = c.Id
        INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        WHERE aip.CreatedTimeStamp >= @ThresholdTime 
           OR aip.UpdatedTimeStamp >= @ThresholdTime
        
        -- UNION
        
        ---- 31. ActivityImageProofs via Calving
        --SELECT DISTINCT cc.FarmId
        --FROM [dbo].[ActivityImageProofs] aip
        --INNER JOIN [dbo].[tbl_Calving] cal ON cal.CalvingGuid = aip.ActivityId
        ---- INNER JOIN [dbo].[BreedCycle] bc ON cal. = bc.Id
        --INNER JOIN [dbo].[Cattles] c ON bc.CattleId = c.Id
        --INNER JOIN [dbo].[CattleContracts] cc ON c.Id = cc.CattleId
        --WHERE aip.CreatedTimeStamp >= @ThresholdTime 
        --   OR aip.UpdatedTimeStamp >= @ThresholdTime
    ) AS CombinedResults
    ORDER BY FarmId
    
END
GO

-- =============================================
-- Usage Examples:
-- =============================================
-- Get farms updated in last 30 minutes (default)
-- EXEC [dbo].[usp_GetRecentlyUpdatedFarmIds]
--
-- Get farms updated in last 60 minutes
-- EXEC [dbo].[usp_GetRecentlyUpdatedFarmIds] 60
--
-- Get farms updated in last 5 minutes
-- EXEC [dbo].[usp_GetRecentlyUpdatedFarmIds] 5
-- =============================================