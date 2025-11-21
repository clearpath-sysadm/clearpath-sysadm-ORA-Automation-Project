-- ============================================================================
-- DUPLICATE ORDERS REPORT - Production SQL Script
-- ============================================================================
-- Purpose: Generate comprehensive report of duplicate orders detected in ShipStation
-- Run this in your production database to see current duplicates
-- Generated: 2025-11-21
-- ============================================================================

-- Set display formatting
\pset border 2
\pset format wrapped

-- ============================================================================
-- SECTION 1: Summary of All Duplicate Alerts
-- ============================================================================
\echo ''
\echo '============================================================================'
\echo 'DUPLICATE ORDER ALERTS - SUMMARY'
\echo '============================================================================'
\echo ''

SELECT 
    id,
    order_number,
    base_sku,
    duplicate_count,
    status,
    shipstation_ids,
    first_detected,
    last_seen,
    resolved_at,
    resolved_by,
    notes
FROM duplicate_order_alerts
ORDER BY 
    CASE WHEN status != 'resolved' THEN 0 ELSE 1 END,
    order_number,
    base_sku;

-- ============================================================================
-- SECTION 2: Detailed Breakdown - Unresolved Duplicates Only
-- ============================================================================
\echo ''
\echo '============================================================================'
\echo 'UNRESOLVED DUPLICATES - DETAILED REPORT'
\echo '============================================================================'
\echo ''

WITH unresolved_duplicates AS (
    SELECT DISTINCT 
        order_number,
        base_sku,
        duplicate_count,
        shipstation_ids,
        first_detected,
        last_seen
    FROM duplicate_order_alerts
    WHERE status != 'resolved'
)
SELECT 
    '--- ORDER #' || ud.order_number || ' + SKU ' || ud.base_sku || ' ---' as section_header,
    ud.duplicate_count as total_duplicates,
    ud.shipstation_ids as all_shipstation_ids,
    ud.first_detected,
    ud.last_seen,
    
    -- Local database records
    (SELECT COUNT(*) 
     FROM orders_inbox oi
     JOIN order_items_inbox oii ON oi.id = oii.order_inbox_id
     WHERE oi.order_number = ud.order_number 
       AND oii.sku LIKE ud.base_sku || '%'
    ) as local_db_records,
    
    -- Details from orders_inbox
    (SELECT string_agg(
        'Local ID: ' || oi.id || 
        ' | SS ID: ' || COALESCE(oi.shipstation_order_id::text, 'NULL') ||
        ' | Status: ' || oi.status ||
        ' | Created: ' || oi.created_at::text,
        E'\n     '
     )
     FROM orders_inbox oi
     JOIN order_items_inbox oii ON oi.id = oii.order_inbox_id
     WHERE oi.order_number = ud.order_number 
       AND oii.sku LIKE ud.base_sku || '%'
    ) as local_db_details

FROM unresolved_duplicates ud
ORDER BY ud.order_number, ud.base_sku;

-- ============================================================================
-- SECTION 3: Count by Status
-- ============================================================================
\echo ''
\echo '============================================================================'
\echo 'DUPLICATE ALERTS BY STATUS'
\echo '============================================================================'
\echo ''

SELECT 
    status,
    COUNT(*) as alert_count,
    COUNT(DISTINCT order_number) as unique_orders,
    MIN(first_detected) as earliest_detection,
    MAX(last_seen) as most_recent_detection
FROM duplicate_order_alerts
GROUP BY status
ORDER BY 
    CASE 
        WHEN status = 'active' THEN 1
        WHEN status = 'pending' THEN 2
        WHEN status = 'resolved' THEN 3
        ELSE 4
    END;

-- ============================================================================
-- SECTION 4: Orders with Multiple Versions in Local Database
-- ============================================================================
\echo ''
\echo '============================================================================'
\echo 'ORDERS WITH MULTIPLE VERSIONS IN LOCAL DATABASE'
\echo '============================================================================'
\echo ''

SELECT 
    oi.order_number,
    COUNT(DISTINCT oi.id) as version_count,
    string_agg(DISTINCT oi.status, ', ') as statuses,
    string_agg(DISTINCT oi.shipstation_order_id::text, ', ') as shipstation_ids,
    MIN(oi.created_at) as first_created,
    MAX(oi.created_at) as last_created
FROM orders_inbox oi
GROUP BY oi.order_number
HAVING COUNT(DISTINCT oi.id) > 1
ORDER BY oi.order_number;

-- ============================================================================
-- SECTION 5: Recent Duplicate Detections (Last 7 Days)
-- ============================================================================
\echo ''
\echo '============================================================================'
\echo 'RECENTLY DETECTED DUPLICATES (Last 7 Days)'
\echo '============================================================================'
\echo ''

SELECT 
    order_number,
    base_sku,
    duplicate_count,
    status,
    shipstation_ids,
    first_detected,
    last_seen,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - first_detected))/3600 as hours_since_detection
FROM duplicate_order_alerts
WHERE first_detected >= CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY first_detected DESC;

-- ============================================================================
-- SECTION 6: Excluded Duplicates (Permanently Ignored)
-- ============================================================================
\echo ''
\echo '============================================================================'
\echo 'PERMANENTLY EXCLUDED DUPLICATES'
\echo '============================================================================'
\echo ''

SELECT 
    order_number,
    base_sku,
    excluded_at,
    excluded_by,
    exclusion_reason
FROM excluded_duplicate_orders
ORDER BY excluded_at DESC;

-- ============================================================================
-- END OF REPORT
-- ============================================================================
\echo ''
\echo '============================================================================'
\echo 'END OF DUPLICATE ORDERS REPORT'
\echo '============================================================================'
\echo ''

-- Optional: Export to CSV
-- To export results to CSV files, uncomment the following lines:
-- \copy (SELECT * FROM duplicate_order_alerts WHERE status != 'resolved' ORDER BY order_number, base_sku) TO '/tmp/unresolved_duplicates.csv' CSV HEADER;
-- \echo 'Exported unresolved duplicates to /tmp/unresolved_duplicates.csv'
