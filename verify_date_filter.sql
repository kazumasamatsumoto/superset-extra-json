-- =====================================================
-- 期間フィルター検証用SQL
-- =====================================================

-- 現在の日付を確認
SELECT CURRENT_DATE as today;

-- =====================================================
-- ケース1: 全期間（フィルターなし）
-- =====================================================
SELECT
    '全期間' as filter_name,
    status,
    COUNT(*) as count,
    SUM(amount) as total_amount
FROM (
    SELECT
        amount,
        CASE
            WHEN (CURRENT_DATE - order_date) < 7 THEN '新規'
            WHEN (CURRENT_DATE - order_date) < 30 THEN '進行中'
            ELSE '遅延'
        END AS status
    FROM orders
) AS orders_with_status
GROUP BY status
ORDER BY status;

-- =====================================================
-- ケース2: Last 7 days（直近7日間）
-- =====================================================
SELECT
    'Last 7 days' as filter_name,
    status,
    COUNT(*) as count,
    SUM(amount) as total_amount
FROM (
    SELECT
        amount,
        CASE
            WHEN (CURRENT_DATE - order_date) < 7 THEN '新規'
            WHEN (CURRENT_DATE - order_date) < 30 THEN '進行中'
            ELSE '遅延'
        END AS status
    FROM orders
    WHERE order_date >= CURRENT_DATE - INTERVAL '7 days'  -- ★期間フィルター
) AS orders_with_status
GROUP BY status
ORDER BY status;

-- 詳細データ確認
SELECT
    'Last 7 days - 詳細' as filter_name,
    order_id,
    order_date,
    customer_name,
    amount,
    department_id,
    (CURRENT_DATE - order_date) as days_ago,
    CASE
        WHEN (CURRENT_DATE - order_date) < 7 THEN '新規'
        WHEN (CURRENT_DATE - order_date) < 30 THEN '進行中'
        ELSE '遅延'
    END AS status
FROM orders
WHERE order_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY order_date DESC;

-- =====================================================
-- ケース3: Last 30 days（直近30日間）
-- =====================================================
SELECT
    'Last 30 days' as filter_name,
    status,
    COUNT(*) as count,
    SUM(amount) as total_amount
FROM (
    SELECT
        amount,
        CASE
            WHEN (CURRENT_DATE - order_date) < 7 THEN '新規'
            WHEN (CURRENT_DATE - order_date) < 30 THEN '進行中'
            ELSE '遅延'
        END AS status
    FROM orders
    WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'  -- ★期間フィルター
) AS orders_with_status
GROUP BY status
ORDER BY status;

-- 詳細データ確認
SELECT
    'Last 30 days - 詳細' as filter_name,
    order_id,
    order_date,
    customer_name,
    amount,
    department_id,
    (CURRENT_DATE - order_date) as days_ago,
    CASE
        WHEN (CURRENT_DATE - order_date) < 7 THEN '新規'
        WHEN (CURRENT_DATE - order_date) < 30 THEN '進行中'
        ELSE '遅延'
    END AS status
FROM orders
WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY order_date DESC;

-- =====================================================
-- ケース4: Last 60 days（直近60日間）
-- =====================================================
SELECT
    'Last 60 days' as filter_name,
    status,
    COUNT(*) as count,
    SUM(amount) as total_amount
FROM (
    SELECT
        amount,
        CASE
            WHEN (CURRENT_DATE - order_date) < 7 THEN '新規'
            WHEN (CURRENT_DATE - order_date) < 30 THEN '進行中'
            ELSE '遅延'
        END AS status
    FROM orders
    WHERE order_date >= CURRENT_DATE - INTERVAL '60 days'  -- ★期間フィルター
) AS orders_with_status
GROUP BY status
ORDER BY status;

-- =====================================================
-- ケース5: 特定期間（例: 2025-12-01 ~ 2026-01-10）
-- =====================================================
SELECT
    '2025-12-01 ~ 2026-01-10' as filter_name,
    status,
    COUNT(*) as count,
    SUM(amount) as total_amount
FROM (
    SELECT
        amount,
        CASE
            WHEN (CURRENT_DATE - order_date) < 7 THEN '新規'
            WHEN (CURRENT_DATE - order_date) < 30 THEN '進行中'
            ELSE '遅延'
        END AS status
    FROM orders
    WHERE order_date BETWEEN '2025-12-01' AND '2026-01-10'  -- ★期間フィルター
) AS orders_with_status
GROUP BY status
ORDER BY status;

-- 詳細データ確認
SELECT
    '2025-12-01 ~ 2026-01-10 - 詳細' as filter_name,
    order_id,
    order_date,
    customer_name,
    amount,
    department_id,
    (CURRENT_DATE - order_date) as days_ago,
    CASE
        WHEN (CURRENT_DATE - order_date) < 7 THEN '新規'
        WHEN (CURRENT_DATE - order_date) < 30 THEN '進行中'
        ELSE '遅延'
    END AS status
FROM orders
WHERE order_date BETWEEN '2025-12-01' AND '2026-01-10'
ORDER BY order_date DESC;

-- =====================================================
-- まとめ: 期待される結果
-- =====================================================
/*
現在日: 2026-01-11

【全期間】
- 新規（0-6日前）: 3件 ¥48,000 (顧客I, A, B)
- 進行中（7-29日前）: 5件 ¥98,000 (顧客J, C, D, E, F)
- 遅延（30日以上前）: 2件 ¥75,000 (顧客G, H)

【Last 7 days】(2026-01-04 ~)
- 新規: 3件 ¥48,000 (顧客I, A, B)
- 進行中: 0件
- 遅延: 0件

【Last 30 days】(2025-12-12 ~)
- 新規: 3件 ¥48,000 (顧客I, A, B)
- 進行中: 4件 ¥86,000 (顧客J, C, D, E)
- 遅延: 0件
※ 顧客Fは30日前（境界線）なので除外される可能性

【Last 60 days】(2025-11-12 ~)
- 新規: 3件 ¥48,000
- 進行中: 5件 ¥98,000
- 遅延: 2件 ¥75,000
全データが含まれる

【2025-12-01 ~ 2026-01-10】
- 新規: 2件 ¥40,000 (顧客A, B) ※ 顧客Iは2026-01-09なので含まれる可能性
- 進行中: 5件 ¥98,000 (顧客J, C, D, E, F)
- 遅延: 1件 ¥40,000 (顧客G)
*/
