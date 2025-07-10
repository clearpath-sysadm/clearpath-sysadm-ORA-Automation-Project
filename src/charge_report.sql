
-- Define the start and end dates for your Golden Test Data period
DECLARE @GoldenPeriodStart DATE = '2025-05-10';
DECLARE @GoldenPeriodEnd DATE = '2025-05-16';

-- Define the start and end dates for your Golden Report Output period
DECLARE @GoldenReportStart DATE = '2025-05-10';
DECLARE @GoldenReportEnd DATE = '2025-05-16';

WITH
-- 1. Get configuration values from Golden_Config_Data
GoldenConfig AS (
    SELECT
        ParameterCategory,
        ParameterName,
        SKU,
        Value
    FROM dbo.Golden_Config_Data
),
Rates AS (
    SELECT
        [OrderCharge] = MAX(CAST(CASE WHEN ParameterName = 'OrderCharge' THEN Value END AS DECIMAL(10,2))),
        [PackageCharge] = MAX(CAST(CASE WHEN ParameterName = 'PackageCharge' THEN Value END AS DECIMAL(10,2))),
        [SpaceRentalRate] = MAX(CAST(CASE WHEN ParameterName = 'SpaceRentalRate' THEN Value END AS DECIMAL(10,2)))
    FROM GoldenConfig
    WHERE ParameterCategory = 'Rates'
    GROUP BY ParameterCategory
),
PalletCounts AS (
    SELECT
        SKU,
        CAST(Value AS INT) AS PalletCount
    FROM GoldenConfig
    WHERE ParameterCategory = 'PalletConfig'
),
InitialInventory AS (
    SELECT
        SKU,
        CAST(Value AS INT) AS EOD_Prior_Week_Qty
    FROM GoldenConfig
    WHERE ParameterCategory = 'InitialInventory'
),

-- 2. Consolidate Raw Data for Golden Test Data (Pulled directly from SQL tables)
GoldenRawDataConsolidated AS (
    -- Data from MayShippedItems
    SELECT
        ShipDate AS [Date],
        SKU_Lot AS SKU_With_Lot,
        QuantityShipped AS Quantity_Shipped,
        NULL AS Order_Number,
        NULL AS Inventory_SKU,
        NULL AS Quantity_Received,
        NULL AS Quantity_Repacked,
        'ShippedItem' AS Transaction_Type
    FROM dbo.MayShippedItems
    WHERE ShipDate BETWEEN @GoldenPeriodStart AND @GoldenPeriodEnd

    UNION ALL

    -- Data from MayShippedOrders
    SELECT
        ShipDate AS [Date],
        NULL AS SKU_With_Lot,
        NULL AS Quantity_Shipped,
        OrderNumber AS Order_Number,
        NULL AS Inventory_SKU,
        NULL AS Quantity_Received,
        NULL AS Quantity_Repacked,
        'ShippedOrder' AS Transaction_Type
    FROM dbo.MayShippedOrders
    WHERE ShipDate BETWEEN @GoldenPeriodStart AND @GoldenPeriodEnd

    UNION ALL

    -- Data from MayReceivedInventory
    SELECT
        ReceiveDate AS [Date],
        NULL AS SKU_With_Lot,
        NULL AS Quantity_Shipped,
        NULL AS Order_Number,
        SKU AS Inventory_SKU,
        QuantityReceived AS Quantity_Received,
        NULL AS Quantity_Repacked,
        'ReceivedInv' AS Transaction_Type
    FROM dbo.MayReceivedInventory
    WHERE ReceiveDate BETWEEN @GoldenPeriodStart AND @GoldenPeriodEnd

    UNION ALL

    -- Data from MayRepackedInventory
    SELECT
        RepackDate AS [Date],
        NULL AS SKU_With_Lot,
        NULL AS Quantity_Shipped,
        NULL AS Order_Number,
        SKU AS Inventory_SKU,
        NULL AS Quantity_Received,
        QuantityRepacked AS Quantity_Repacked,
        'RepackedInv' AS Transaction_Type
    FROM dbo.MayRepackedInventory
    WHERE RepackDate BETWEEN @GoldenPeriodStart AND @GoldenPeriodEnd
),

-- 3. Generate all dates for the Golden Test Data period (for consistency)
GoldenDates AS (
    SELECT @GoldenPeriodStart AS ReportDate
    UNION ALL
    SELECT DATEADD(day, 1, ReportDate)
    FROM GoldenDates
    WHERE ReportDate <= @GoldenPeriodEnd
),

-- 4. Aggregated Daily Shipped Items from GoldenRawDataConsolidated
DailyShippedSKUQty_Golden AS (
    SELECT
        [Date] AS ReportDate,
        LEFT(SKU_With_Lot, CHARINDEX(' - ', SKU_With_Lot) - 1) AS BaseSKU,
        SUM(Quantity_Shipped) AS TotalQtyShipped
    FROM GoldenRawDataConsolidated
    WHERE Transaction_Type = 'ShippedItem'
    GROUP BY [Date], LEFT(SKU_With_Lot, CHARINDEX(' - ', SKU_With_Lot) - 1)
),

-- 5. Aggregated Daily Unique Order Count from GoldenRawDataConsolidated
DailyOrderCount_Golden AS (
    SELECT
        [Date] AS ReportDate,
        COUNT(DISTINCT Order_Number) AS CountOfOrders
    FROM GoldenRawDataConsolidated
    WHERE Transaction_Type = 'ShippedOrder'
    GROUP BY [Date]
),

-- 6. Aggregated Daily Inventory Movements (Received and Repacked) from GoldenRawDataConsolidated
DailyInventoryMovements_Golden AS (
    SELECT
        [Date] AS MovementDate,
        Inventory_SKU AS SKU,
        SUM(ISNULL(Quantity_Received, 0)) AS ReceivedQty,
        SUM(ISNULL(Quantity_Repacked, 0)) AS RepackedQty
    FROM GoldenRawDataConsolidated
    WHERE Transaction_Type IN ('ReceivedInv', 'RepackedInv')
    GROUP BY [Date], Inventory_SKU
),

-- 7. Consolidated all daily SKU movements for the Golden Period, filling in zeros
AllDailySKUMovements_Golden AS (
    SELECT
        GD.ReportDate AS MovementDate,
        PC.SKU,
        ISNULL(DSQ.TotalQtyShipped, 0) AS ShippedQty,
        ISNULL(DIM.ReceivedQty, 0) AS ReceivedQty,
        ISNULL(DIM.RepackedQty, 0) AS RepackedQty
    FROM GoldenDates GD
    CROSS JOIN PalletCounts PC
    LEFT JOIN DailyShippedSKUQty_Golden DSQ
        ON GD.ReportDate = DSQ.ReportDate AND PC.SKU = DSQ.BaseSKU
    LEFT JOIN DailyInventoryMovements_Golden DIM
        ON GD.ReportDate = DIM.MovementDate AND PC.SKU = DIM.SKU
),

-- 8. Recursive CTE for Daily Inventory (BOD and EOD) for Golden Test
DailyInventory_Golden AS (
    -- Anchor Member: Start with the EOD from the day PRIOR to the Golden Period Start (May 9th)
    SELECT
        CAST('2025-05-09' AS DATE) AS InventoryDate, -- Explicitly cast to DATE
        II.SKU,
        II.EOD_Prior_Week_Qty AS BOD_Qty,
        0 AS ShippedQty,
        0 AS ReceivedQty,
        0 AS RepackedQty,
        II.EOD_Prior_Week_Qty AS EOD_Qty
    FROM InitialInventory II

    UNION ALL

    -- Recursive Member: Calculate for subsequent days within the golden period
    SELECT
        DATEADD(day, 1, DI.InventoryDate) AS InventoryDate,
        DI.SKU,
        DI.EOD_Qty AS BOD_Qty,
        ADSM.ShippedQty,
        ADSM.ReceivedQty,
        ADSM.RepackedQty,
        DI.EOD_Qty
        - ADSM.ShippedQty
        + ADSM.ReceivedQty
        + ADSM.RepackedQty
        AS EOD_Qty
    FROM DailyInventory_Golden DI
    INNER JOIN GoldenDates GD_Next
        ON DATEADD(day, 1, DI.InventoryDate) = GD_Next.ReportDate
    INNER JOIN AllDailySKUMovements_Golden ADSM
        ON GD_Next.ReportDate = ADSM.MovementDate AND DI.SKU = ADSM.SKU
    WHERE DI.InventoryDate < @GoldenReportEnd
),

-- 9. Calculate Daily Space Rental per SKU for Golden Test
DailySpaceRentalCalc_Golden AS (
    SELECT
        DI.InventoryDate AS ReportDate,
        DI.SKU,
        DI.EOD_Qty,
        PC.PalletCount,
        CASE WHEN PC.PalletCount = 0 THEN 0 ELSE CEILING(CAST(DI.EOD_Qty AS DECIMAL(10,2)) / PC.PalletCount) END AS PalletsUsed,
        CASE WHEN PC.PalletCount = 0 THEN 0 ELSE CEILING(CAST(DI.EOD_Qty AS DECIMAL(10,2)) / PC.PalletCount) END * Rates.SpaceRentalRate AS SpaceRentalPerSKU
    FROM DailyInventory_Golden DI
    JOIN PalletCounts PC ON DI.SKU = PC.SKU
    CROSS JOIN Rates
    WHERE DI.EOD_Qty > 0
      AND DI.InventoryDate BETWEEN @GoldenReportStart AND @GoldenReportEnd
)

-- Final SELECT for Golden_Test_Data_Expected_Output
SELECT
    GD.ReportDate AS [Date],
    ISNULL(DOC.CountOfOrders, 0) AS [# Of Orders],
    ISNULL(DSQ_17612.TotalQtyShipped, 0) AS [17612_Shipped],
    ISNULL(DSQ_17904.TotalQtyShipped, 0) AS [17904_Shipped],
    ISNULL(DSQ_17914.TotalQtyShipped, 0) AS [17914_Shipped],
    ISNULL(DSQ_18675.TotalQtyShipped, 0) AS [18675_Shipped],
    Rates.OrderCharge * ISNULL(DOC.CountOfOrders, 0) AS [Orders_Charge],
    Rates.PackageCharge * (ISNULL(DSQ_17612.TotalQtyShipped, 0) + ISNULL(DSQ_17904.TotalQtyShipped, 0) + ISNULL(DSQ_17914.TotalQtyShipped, 0) + ISNULL(DSQ_18675.TotalQtyShipped, 0)) AS [Packages_Charge],
    ISNULL(SUM(DSRC.SpaceRentalPerSKU), 0) AS [Space_Rental_Charge],
    (Rates.OrderCharge * ISNULL(DOC.CountOfOrders, 0)) +
    (Rates.PackageCharge * (ISNULL(DSQ_17612.TotalQtyShipped, 0) + ISNULL(DSQ_17904.TotalQtyShipped, 0) + ISNULL(DSQ_17914.TotalQtyShipped, 0) + ISNULL(DSQ_18675.TotalQtyShipped, 0))) +
    ISNULL(SUM(DSRC.SpaceRentalPerSKU), 0) AS [Total_Charge],

    -- Intermediate Inventory values for validation
    DI_17612.BOD_Qty AS [17612_BOD],
    DI_17612.ShippedQty AS [17612_Shipped_Daily],
    DI_17612.ReceivedQty AS [17612_Received_Daily],
    DI_17612.RepackedQty AS [17612_Repacked_Daily],
    DI_17612.EOD_Qty AS [17612_EOD],

    DI_17904.BOD_Qty AS [17904_BOD],
    DI_17904.ShippedQty AS [17904_Shipped_Daily],
    DI_17904.ReceivedQty AS [17904_Received_Daily],
    DI_17904.RepackedQty AS [17904_Repacked_Daily],
    DI_17904.EOD_Qty AS [17904_EOD],

    DI_17914.BOD_Qty AS [17914_BOD],
    DI_17914.ShippedQty AS [17914_Shipped_Daily],
    DI_17914.ReceivedQty AS [17914_Received_Daily],
    DI_17914.RepackedQty AS [17914_Repacked_Daily],
    DI_17914.EOD_Qty AS [17914_EOD],

    DI_18675.BOD_Qty AS [18675_BOD],
    DI_18675.ShippedQty AS [18675_Shipped_Daily],
    DI_18675.ReceivedQty AS [18675_Received_Daily],
    DI_18675.RepackedQty AS [18675_Repacked_Daily],
    DI_18675.EOD_Qty AS [18675_EOD]

FROM GoldenDates GD
LEFT JOIN DailyOrderCount_Golden DOC ON GD.ReportDate = DOC.ReportDate
LEFT JOIN DailyShippedSKUQty_Golden DSQ_17612 ON GD.ReportDate = DSQ_17612.ReportDate AND DSQ_17612.BaseSKU = '17612'
LEFT JOIN DailyShippedSKUQty_Golden DSQ_17904 ON GD.ReportDate = DSQ_17904.ReportDate AND DSQ_17904.BaseSKU = '17904'
LEFT JOIN DailyShippedSKUQty_Golden DSQ_17914 ON GD.ReportDate = DSQ_17914.ReportDate AND DSQ_17914.BaseSKU = '17914'
LEFT JOIN DailyShippedSKUQty_Golden DSQ_18675 ON GD.ReportDate = DSQ_18675.ReportDate AND DSQ_18675.BaseSKU = '18675'
LEFT JOIN DailySpaceRentalCalc_Golden DSRC ON GD.ReportDate = DSRC.ReportDate
CROSS JOIN Rates
LEFT JOIN DailyInventory_Golden DI_17612 ON GD.ReportDate = DI_17612.InventoryDate AND DI_17612.SKU = '17612'
LEFT JOIN DailyInventory_Golden DI_17904 ON GD.ReportDate = DI_17904.InventoryDate AND DI_17904.SKU = '17904'
LEFT JOIN DailyInventory_Golden DI_17914 ON GD.ReportDate = DI_17914.InventoryDate AND DI_17914.SKU = '17914'
LEFT JOIN DailyInventory_Golden DI_18675 ON GD.ReportDate = DI_18675.InventoryDate AND DI_18675.SKU = '18675'

GROUP BY
    GD.ReportDate,
    ISNULL(DOC.CountOfOrders, 0),
    ISNULL(DSQ_17612.TotalQtyShipped, 0),
    ISNULL(DSQ_17904.TotalQtyShipped, 0),
    ISNULL(DSQ_17914.TotalQtyShipped, 0),
    ISNULL(DSQ_18675.TotalQtyShipped, 0),
    DI_17612.BOD_Qty, DI_17612.ShippedQty, DI_17612.ReceivedQty, DI_17612.RepackedQty, DI_17612.EOD_Qty,
    DI_17904.BOD_Qty, DI_17904.ShippedQty, DI_17904.ReceivedQty, DI_17904.RepackedQty, DI_17904.EOD_Qty,
    DI_17914.BOD_Qty, DI_17914.ShippedQty, DI_17914.ReceivedQty, DI_17914.RepackedQty, DI_17914.EOD_Qty,
    DI_18675.BOD_Qty, DI_18675.ShippedQty, DI_18675.ReceivedQty, DI_18675.RepackedQty, DI_18675.EOD_Qty,
    Rates.OrderCharge, Rates.PackageCharge
ORDER BY [Date]
OPTION (MAXRECURSION 31);