# クロスフィルタリング要件 - ステータス計算を含む動的フィルタリング

## 要件

### 1. 期間検索（Dashboard Filter）
- ユーザーが期間を選択（例: 2024-01-01 〜 2024-03-31）
- **この期間フィルターは元データに対して適用される**

### 2. ステータス計算（SQL内で計算）
期間検索後のデータに対して、SQLでステータスを計算：

```sql
SELECT
    order_id,
    order_date,
    amount,
    customer_name,
    CASE
        WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 7 THEN '新規'
        WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 30 THEN '進行中'
        ELSE '遅延'
    END AS status
FROM orders
WHERE order_date BETWEEN '2024-01-01' AND '2024-03-31'  -- 期間フィルター
```

### 3. 円グラフ（ステータス別集計）
ステータス別に金額を集計：

```sql
SELECT
    status,
    SUM(amount) as total_amount
FROM (
    SELECT
        amount,
        CASE
            WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 7 THEN '新規'
            WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 30 THEN '進行中'
            ELSE '遅延'
        END AS status
    FROM orders
    WHERE order_date BETWEEN '2024-01-01' AND '2024-03-31'
) AS orders_with_status
GROUP BY status
```

### 4. 円グラフクリック → テーブル表示
ユーザーが円グラフで「進行中」をクリック
→ 「進行中」ステータスのデータのみをテーブルに表示

```sql
SELECT
    order_id,
    order_date,
    amount,
    customer_name,
    status
FROM (
    SELECT
        order_id,
        order_date,
        amount,
        customer_name,
        CASE
            WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 7 THEN '新規'
            WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 30 THEN '進行中'
            ELSE '遅延'
        END AS status
    FROM orders
    WHERE order_date BETWEEN '2024-01-01' AND '2024-03-31'  -- 期間フィルター
) AS orders_with_status
WHERE status = '進行中'  -- 円グラフクリックで追加されるフィルター
```

## 問題点

### 問題1: ステータスはSQLで計算される（Virtual Column）
- ステータスは物理的なカラムではなく、CASE WHEN で計算される
- 期間が変われば、同じレコードでもステータスが変わる可能性がある
  - 例: 2024-01-01のレコード
    - 2024-01-05時点: 「新規」
    - 2024-02-01時点: 「進行中」

### 問題2: 円グラフとテーブルで同じステータス計算が必要
- 円グラフ用Chart: `GROUP BY status`
- テーブル用Chart: `WHERE status = 'XX'`
- **両方で同じCASE WHENロジックを共有する必要がある**

### 問題3: クロスフィルタリングの実現方法
Supersetでは、Chart間のフィルタリングを実現する方法：
1. **Dashboard Filter** - 全Chartに適用されるグローバルフィルター
2. **Cross-Filter** - Chartをクリックして他のChartをフィルタリング（Superset 2.0+）
3. **Native Filter** - ユーザーが選択するフィルター

## 解決策の候補

### 案1: Virtual Dataset with Calculated Status ⭐ 推奨

#### Dataset SQL
```sql
SELECT
    order_id,
    order_date,
    amount,
    customer_name,
    department_id,
    CASE
        WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 7 THEN '新規'
        WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 30 THEN '進行中'
        ELSE '遅延'
    END AS status,
    EXTRACT(DAY FROM (CURRENT_DATE - order_date)) AS days_since_order
FROM orders
```

このDatasetに対して：
- **Chart 1 (円グラフ)**: `SELECT status, SUM(amount) FROM dataset GROUP BY status`
- **Chart 2 (テーブル)**: `SELECT * FROM dataset`
- **Dashboard Filter**: `order_date` でフィルタリング
- **Cross-Filter**: 円グラフクリック → `status` でテーブルをフィルタリング

**メリット**:
- ✅ ステータスロジックがDatasetに1箇所だけ
- ✅ Dashboard FilterとCross-Filterが両立可能
- ✅ 保守性が高い

**デメリット**:
- ⚠️ ステータス計算が現在日時に依存する場合、キャッシュに注意

---

### 案2: SQL Expression Column（物理カラム化）

Datasetに「Calculated Column」を追加：

```python
# Superset UIで設定
Column Name: status
SQL Expression:
CASE
    WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 7 THEN '新規'
    WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 30 THEN '進行中'
    ELSE '遅延'
END
```

**メリット**:
- ✅ Superset UIで管理可能
- ✅ Chart作成時にカラムとして選択可能

**デメリット**:
- ⚠️ Physical TableのDatasetでは使えない（Virtual Datasetのみ）

---

### 案3: Jinja Template + Dashboard Filter

Dataset SQLにJinja Templateを使用：

```sql
SELECT
    order_id,
    order_date,
    amount,
    customer_name,
    CASE
        WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 7 THEN '新規'
        WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 30 THEN '進行中'
        ELSE '遅延'
    END AS status
FROM orders
WHERE order_date BETWEEN '{{ from_dttm }}' AND '{{ to_dttm }}'
```

**メリット**:
- ✅ 期間フィルターをSQL内に埋め込める

**デメリット**:
- ❌ Dashboard Filterが動的に機能しない（固定値になる）
- ❌ Cross-Filterとの組み合わせが困難

---

## 推奨実装: 案1の詳細

### Step 1: サンプルデータ作成

```sql
-- PostgreSQLで実行
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    order_date DATE NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    customer_name VARCHAR(100),
    department_id INT
);

-- サンプルデータ挿入
INSERT INTO orders (order_date, amount, customer_name, department_id) VALUES
('2024-01-05', 15000, '顧客A', 101),
('2024-01-10', 25000, '顧客B', 101),
('2024-01-20', 18000, '顧客C', 102),
('2024-02-01', 30000, '顧客D', 102),
('2024-02-15', 22000, '顧客E', 103),
('2024-03-01', 12000, '顧客F', 103),
('2023-12-15', 40000, '顧客G', 101);  -- 古いデータ
```

### Step 2: Virtual Dataset作成

```sql
SELECT
    order_id,
    order_date,
    amount,
    customer_name,
    department_id,
    CASE
        WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 7 THEN '新規'
        WHEN EXTRACT(DAY FROM (CURRENT_DATE - order_date)) < 30 THEN '進行中'
        ELSE '遅延'
    END AS status,
    EXTRACT(DAY FROM (CURRENT_DATE - order_date)) AS days_since_order
FROM orders
```

Dataset名: `orders_with_status`

### Step 3: Chart作成

#### Chart 1: 円グラフ（ステータス別金額）
- Chart Type: Pie Chart
- Dataset: `orders_with_status`
- Dimension: `status`
- Metric: `SUM(amount)`

#### Chart 2: テーブル（詳細データ）
- Chart Type: Table
- Dataset: `orders_with_status`
- Columns: `order_id`, `order_date`, `customer_name`, `amount`, `status`, `days_since_order`
- Sort: `order_date DESC`

### Step 4: Dashboard設定

1. **Dashboard Filter追加**
   - Filter Name: 期間
   - Column: `order_date`
   - Filter Type: Time Range

2. **Cross-Filter有効化**
   - Dashboard Settings → Advanced
   - Enable "Cross-filtering"
   - 円グラフをクリック → テーブルがフィルタリングされる

### Step 5: RLSによる部署フィルタリング（既存機能）

Guest Token生成時に部署フィルタを追加：

```typescript
rls_rules: [
  {
    clause: `department_id = ${departmentId}`
  }
]
```

これにより、**期間フィルター + ステータスフィルター + 部署フィルター**の3段階フィルタリングが実現。

---

## 次のステップ

実際にサンプルデータを作成して動作確認しますか？
1. PostgreSQLにordersテーブル作成
2. サンプルデータ投入
3. Superset DatasetとChart作成
4. Cross-Filter動作確認
