-- =====================================================
-- 不具合率分析用のサンプルデータ作成
-- =====================================================

-- テーブル作成: 製品テスト結果（日次）
DROP TABLE IF EXISTS product_test_results CASCADE;

CREATE TABLE product_test_results (
    id SERIAL PRIMARY KEY,
    test_date DATE NOT NULL,
    product_name VARCHAR(100) NOT NULL,  -- 製品名（例: iPhone 14, Galaxy S23）
    product_category VARCHAR(50),        -- カテゴリ（例: スマートフォン、タブレット）
    department_id INT,                   -- 部署ID（RLS用）
    success_count INT NOT NULL,          -- 成功数
    failure_count INT NOT NULL,          -- 失敗数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- サンプルデータ投入
INSERT INTO product_test_results (test_date, product_name, product_category, department_id, success_count, failure_count) VALUES
-- iPhone 14: 1月は良好、2月は不具合増加
('2024-01-05', 'iPhone 14', 'スマートフォン', 101, 95, 5),    -- 不具合率5%
('2024-01-12', 'iPhone 14', 'スマートフォン', 101, 98, 2),    -- 不具合率2%
('2024-01-19', 'iPhone 14', 'スマートフォン', 101, 97, 3),    -- 不具合率3%
('2024-01-26', 'iPhone 14', 'スマートフォン', 101, 96, 4),    -- 不具合率4%
('2024-02-02', 'iPhone 14', 'スマートフォン', 101, 85, 15),   -- 不具合率15%
('2024-02-09', 'iPhone 14', 'スマートフォン', 101, 82, 18),   -- 不具合率18%
('2024-02-16', 'iPhone 14', 'スマートフォン', 101, 80, 20),   -- 不具合率20%
('2024-02-23', 'iPhone 14', 'スマートフォン', 101, 83, 17),   -- 不具合率17%

-- Galaxy S23: 安定して良好
('2024-01-05', 'Galaxy S23', 'スマートフォン', 102, 98, 2),   -- 不具合率2%
('2024-01-12', 'Galaxy S23', 'スマートフォン', 102, 97, 3),   -- 不具合率3%
('2024-01-19', 'Galaxy S23', 'スマートフォン', 102, 99, 1),   -- 不具合率1%
('2024-01-26', 'Galaxy S23', 'スマートフォン', 102, 98, 2),   -- 不具合率2%
('2024-02-02', 'Galaxy S23', 'スマートフォン', 102, 96, 4),   -- 不具合率4%
('2024-02-09', 'Galaxy S23', 'スマートフォン', 102, 97, 3),   -- 不具合率3%
('2024-02-16', 'Galaxy S23', 'スマートフォン', 102, 98, 2),   -- 不具合率2%
('2024-02-23', 'Galaxy S23', 'スマートフォン', 102, 99, 1),   -- 不具合率1%

-- Pixel 8: 1月は問題あり、2月は改善
('2024-01-05', 'Pixel 8', 'スマートフォン', 103, 88, 12),     -- 不具合率12%
('2024-01-12', 'Pixel 8', 'スマートフォン', 103, 85, 15),     -- 不具合率15%
('2024-01-19', 'Pixel 8', 'スマートフォン', 103, 87, 13),     -- 不具合率13%
('2024-01-26', 'Pixel 8', 'スマートフォン', 103, 86, 14),     -- 不具合率14%
('2024-02-02', 'Pixel 8', 'スマートフォン', 103, 92, 8),      -- 不具合率8%
('2024-02-09', 'Pixel 8', 'スマートフォン', 103, 94, 6),      -- 不具合率6%
('2024-02-16', 'Pixel 8', 'スマートフォン', 103, 95, 5),      -- 不具合率5%
('2024-02-23', 'Pixel 8', 'スマートフォン', 103, 96, 4);      -- 不具合率4%

-- データ確認
SELECT
    product_name,
    test_date,
    success_count,
    failure_count,
    ROUND(failure_count::NUMERIC / (success_count + failure_count) * 100, 2) as defect_rate_percent
FROM product_test_results
ORDER BY product_name, test_date;

-- =====================================================
-- Virtual Dataset用SQL
-- =====================================================
/*
SELECT
    product_name,
    test_date,
    success_count,
    failure_count,
    department_id,
    -- 不具合率計算
    ROUND(failure_count::NUMERIC / (success_count + failure_count) * 100, 2) as defect_rate,
    -- ステータス判定
    CASE
        WHEN failure_count::NUMERIC / (success_count + failure_count) <= 0.05 THEN 'Good'
        WHEN failure_count::NUMERIC / (success_count + failure_count) <= 0.10 THEN 'Warning'
        ELSE 'Bad'
    END AS status
FROM product_test_results
ORDER BY test_date DESC, product_name
*/

-- =====================================================
-- 期間ごとの集計例
-- =====================================================

-- 例1: 2024年1月のiPhone 14の不具合率
SELECT
    product_name,
    '2024年1月' as period,
    SUM(success_count) as total_success,
    SUM(failure_count) as total_failure,
    SUM(success_count + failure_count) as total_tests,
    ROUND(SUM(failure_count)::NUMERIC / SUM(success_count + failure_count) * 100, 2) as defect_rate,
    CASE
        WHEN SUM(failure_count)::NUMERIC / SUM(success_count + failure_count) <= 0.05 THEN 'Good'
        WHEN SUM(failure_count)::NUMERIC / SUM(success_count + failure_count) <= 0.10 THEN 'Warning'
        ELSE 'Bad'
    END AS status
FROM product_test_results
WHERE product_name = 'iPhone 14'
  AND test_date >= '2024-01-01'
  AND test_date < '2024-02-01'
GROUP BY product_name;

-- 例2: 2024年2月のiPhone 14の不具合率
SELECT
    product_name,
    '2024年2月' as period,
    SUM(success_count) as total_success,
    SUM(failure_count) as total_failure,
    SUM(success_count + failure_count) as total_tests,
    ROUND(SUM(failure_count)::NUMERIC / SUM(success_count + failure_count) * 100, 2) as defect_rate,
    CASE
        WHEN SUM(failure_count)::NUMERIC / SUM(success_count + failure_count) <= 0.05 THEN 'Good'
        WHEN SUM(failure_count)::NUMERIC / SUM(success_count + failure_count) <= 0.10 THEN 'Warning'
        ELSE 'Bad'
    END AS status
FROM product_test_results
WHERE product_name = 'iPhone 14'
  AND test_date >= '2024-02-01'
  AND test_date < '2024-03-01'
GROUP BY product_name;

-- 例3: 全製品の期間別ステータス比較
SELECT
    product_name,
    CASE
        WHEN test_date >= '2024-01-01' AND test_date < '2024-02-01' THEN '2024年1月'
        WHEN test_date >= '2024-02-01' AND test_date < '2024-03-01' THEN '2024年2月'
    END as period,
    SUM(success_count) as total_success,
    SUM(failure_count) as total_failure,
    ROUND(SUM(failure_count)::NUMERIC / SUM(success_count + failure_count) * 100, 2) as defect_rate,
    CASE
        WHEN SUM(failure_count)::NUMERIC / SUM(success_count + failure_count) <= 0.05 THEN 'Good'
        WHEN SUM(failure_count)::NUMERIC / SUM(success_count + failure_count) <= 0.10 THEN 'Warning'
        ELSE 'Bad'
    END AS status
FROM product_test_results
GROUP BY product_name, period
ORDER BY product_name, period;

-- =====================================================
-- 期待される結果
-- =====================================================
/*
【2024年1月】
- iPhone 14: 不具合率 3.5% → Good ✅
- Galaxy S23: 不具合率 2.0% → Good ✅
- Pixel 8: 不具合率 13.5% → Bad ❌

【2024年2月】
- iPhone 14: 不具合率 17.5% → Bad ❌
- Galaxy S23: 不具合率 2.5% → Good ✅
- Pixel 8: 不具合率 5.8% → Warning ⚠️

【1-2月合算】
- iPhone 14: 不具合率 10.5% → Warning ⚠️
- Galaxy S23: 不具合率 2.2% → Good ✅
- Pixel 8: 不具合率 9.6% → Warning ⚠️
*/
