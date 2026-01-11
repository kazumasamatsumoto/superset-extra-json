# RLS の制約: ネストされたGROUP BYには対応できない

## 問題の本質

あなたの指摘は正しいです。RLSには重要な制約があります。

## ケース1: 生データのDataset（現在） ✅ 動作する

### Dataset SQL
```sql
SELECT
    s.id,
    s.sale_date,
    s.amount,
    s.department_id
FROM sales s
```

### ChartでGROUP BYを実行した時のSQL
```sql
SELECT DATE_TRUNC('day', sale_date), SUM(amount)
FROM (
    SELECT s.id, s.sale_date, s.amount, s.department_id
    FROM sales s
) AS virtual_table
WHERE (department_id = 101)  -- ★ RLS: GROUP BYの前に適用
GROUP BY DATE_TRUNC('day', sale_date)
```

**結果**: ✅ 正しくフィルタリングされる

---

## ケース2: 集約済みDataset ❌ 正しく動作しない可能性

### Dataset SQL（既にGROUP BY済み）
```sql
SELECT
    department_id,
    DATE_TRUNC('day', sale_date) as sale_date,
    SUM(amount) as total_amount
FROM sales
GROUP BY department_id, DATE_TRUNC('day', sale_date)  -- ★ 内側のGROUP BY
```

この時点で、**全部署のデータが日付ごとに集約されている**：
```
department_id | sale_date  | total_amount
--------------+------------+-------------
101           | 2024-01-15 | 150000
102           | 2024-01-15 | 120000
103           | 2024-01-15 | 80000
101           | 2024-01-16 | 200000
...
```

### ChartでさらにGROUP BYを実行した時のSQL
```sql
SELECT sale_date, SUM(total_amount)
FROM (
    SELECT
        department_id,
        DATE_TRUNC('day', sale_date) as sale_date,
        SUM(amount) as total_amount
    FROM sales
    GROUP BY department_id, DATE_TRUNC('day', sale_date)  -- ★ 全部署で集約済み
) AS virtual_table
WHERE (department_id = 101)  -- ★ RLS: ここでフィルタリング
GROUP BY sale_date  -- ★ 外側のGROUP BY
```

**問題点**:
- 内側のGROUP BYで**既に全部署のデータが日付ごとに別レコードとして存在**
- RLSでフィルタリングしても、**既に集約されたレコードをフィルタリングするだけ**
- この場合は正しく動作する（各部署が別レコードなので）

---

## ケース3: 問題が発生する本当のケース ❌ RLSでは不可能

### Dataset SQL（部署をまたいで集約）
```sql
SELECT
    DATE_TRUNC('day', sale_date) as sale_date,
    SUM(amount) as total_amount,  -- ★ 全部署の合計
    SUM(CASE WHEN department_id = 101 THEN amount ELSE 0 END) as sales_dept,
    SUM(CASE WHEN department_id = 102 THEN amount ELSE 0 END) as dev_dept,
    SUM(CASE WHEN department_id = 103 THEN amount ELSE 0 END) as marketing_dept
FROM sales
GROUP BY DATE_TRUNC('day', sale_date)  -- ★ department_idでGROUP BYしていない
```

この結果：
```
sale_date  | total_amount | sales_dept | dev_dept | marketing_dept
-----------+--------------+------------+----------+---------------
2024-01-15 | 350000       | 150000     | 120000   | 80000
2024-01-16 | 420000       | 200000     | 180000   | 40000
```

### RLSを適用しても無意味
```sql
SELECT sale_date, SUM(total_amount)
FROM (
    SELECT
        DATE_TRUNC('day', sale_date) as sale_date,
        SUM(amount) as total_amount  -- ★ 既に全部署の合計
    FROM sales
    GROUP BY DATE_TRUNC('day', sale_date)
) AS virtual_table
WHERE (department_id = 101)  -- ★ department_idカラムが存在しない！
GROUP BY sale_date
```

**エラー**: `column "department_id" does not exist`

---

## 実際のケース: あなたの環境

### 現在のDataset
```sql
SELECT s.id, s.sale_date, s.amount, s.department_id
FROM sales s
LEFT JOIN departments d ON s.department_id = d.id
```

**これは「生データ」なので、RLSは正しく動作します。**

### もしDatasetが以下のようなものだったら？

```sql
-- 例: 月次集計データ
SELECT
    DATE_TRUNC('month', sale_date) as month,
    department_id,
    SUM(amount) as monthly_total,
    AVG(amount) as avg_transaction
FROM sales
GROUP BY DATE_TRUNC('month', sale_date), department_id
```

**この場合でもRLSは動作します** - なぜなら`department_id`がGROUP BYに含まれているから。

### 問題が発生するのは？

```sql
-- 例: 全社の月次サマリー（部署別の列として展開）
SELECT
    DATE_TRUNC('month', sale_date) as month,
    COUNT(*) as total_transactions,
    SUM(amount) as total_sales,
    COUNT(DISTINCT customer_id) as unique_customers
    -- ★ department_idがない
FROM sales
GROUP BY DATE_TRUNC('month', sale_date)
```

**このようなDatasetに対してはRLSでフィルタリングできません。**

---

## 結論

### あなたの質問への回答

> GROUP Byの中にGroup Byがあるようなデータに対してはできないって話

**正確には**:
- ❌ **Dataset内のGROUP BYでdepartment_idが除外されている場合** → RLS不可能
- ✅ **Dataset内のGROUP BYでdepartment_idが保持されている場合** → RLS可能
- ✅ **DatasetがGROUP BYしていない生データの場合** → RLS可能（現在の環境）

### 現在の環境
- ✅ Dataset = 生データ（GROUP BYなし）
- ✅ RLSは正しく動作する
- ✅ ChartでのGROUP BYの前にフィルタリングが適用される

### 将来的に問題になるケース

もしDatasetを以下のように変更する場合：

```sql
-- 全社サマリー（部署情報を失う）
SELECT
    DATE_TRUNC('day', sale_date) as sale_date,
    SUM(amount) as daily_total  -- 全部署の合計
FROM sales
GROUP BY DATE_TRUNC('day', sale_date)
-- ★ department_idがない
```

**この場合、RLSでは対応できない** → Dataset自体を部署ごとに分けるか、department_idを保持する必要がある

---

## 推奨事項

### ✅ 現在の実装を維持

現在のDataset構造（生データ）は、RLSと相性が良い。このまま継続してOK。

### ✅ Datasetの設計原則

動的フィルタリング（RLS）を使う場合：
1. **Datasetには必ずフィルタリング対象のカラム（department_id等）を保持する**
2. **GROUP BYを使う場合も、フィルタリング対象カラムをGROUP BY句に含める**
3. **集約は極力Chart側で行う（Dataset側では最小限に）**

### ❌ 避けるべきパターン

```sql
-- NG: フィルタリング対象カラムを失う集約
SELECT DATE_TRUNC('day', sale_date), SUM(amount)
FROM sales
GROUP BY DATE_TRUNC('day', sale_date)
-- department_idがない → RLSでフィルタリング不可能
```

---

**検証日**: 2026-01-11
**結論**: 現在の環境ではRLSは正しく動作する。Dataset設計時にフィルタリング対象カラムを保持することが重要。
