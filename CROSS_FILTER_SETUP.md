# クロスフィルター実装手順

## 概要

期間検索 → ステータス計算 → 円グラフ表示 → クリックでテーブルフィルタリング

## サンプルデータ確認

```bash
docker exec superset_db psql -U superset -d superset -c "
SELECT
    status,
    COUNT(*) as count,
    SUM(amount) as total
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
"
```

## Superset設定手順

### 1. Dataset作成

**SQL Lab → SQL Editor** で以下のSQLを実行：

```sql
SELECT
    order_id,
    order_date,
    amount,
    customer_name,
    department_id,
    CASE
        WHEN (CURRENT_DATE - order_date) < 7 THEN '新規'
        WHEN (CURRENT_DATE - order_date) < 30 THEN '進行中'
        ELSE '遅延'
    END AS status,
    (CURRENT_DATE - order_date) AS days_since_order
FROM orders
ORDER BY order_date DESC
```

**「Save」→「Save as Dataset」**
- Dataset名: `orders_with_status`
- Database: `superset`

### 2. Dataset設定の確認

**Data → Datasets → orders_with_status** を開く

**Columns タブで確認**:
- `order_id`: INTEGER
- `order_date`: DATE (「Is temporal」にチェック)
- `amount`: NUMERIC
- `customer_name`: VARCHAR
- `department_id`: INTEGER
- `status`: VARCHAR (「Is filterable」にチェック)
- `days_since_order`: INTEGER

### 3. Chart 1: 円グラフ（ステータス別金額）作成

**Charts → + Create Chart**

#### 基本設定
- Chart Type: `Pie Chart`
- Dataset: `orders_with_status`

#### Data タブ
- **Dimension**: `status`
- **Metric**: `SUM(amount)`
  - Metric名: `Total Amount`

#### Customize タブ
- Chart Title: `ステータス別売上`
- Show Legend: Yes
- Show Labels: Yes

**Save**
- Chart名: `ステータス別売上（円グラフ）`

### 4. Chart 2: テーブル（詳細データ）作成

**Charts → + Create Chart**

#### 基本設定
- Chart Type: `Table`
- Dataset: `orders_with_status`

#### Data タブ
- **Columns**:
  - `order_id`
  - `order_date`
  - `customer_name`
  - `amount`
  - `status`
  - `days_since_order`
- **Sort by**: `order_date` (Descending)
- **Row limit**: 100

#### Customize タブ
- Chart Title: `受注詳細テーブル`

**Save**
- Chart名: `受注詳細テーブル`

### 5. Dashboard作成

**Dashboards → + Dashboard**

#### Dashboard設定
- Dashboard名: `受注ステータス分析`

#### Chart配置
1. 円グラフを上部に配置（幅: 50%）
2. テーブルを下部に配置（幅: 100%）

### 6. Cross-Filter有効化

#### Dashboard Settings

1. Dashboard右上の **「...」→「Edit Dashboard」**
2. 円グラフをクリック → 右側のパネルで **「Chart Configuration」**
3. **「Interaction」** セクション
4. **「Enable Cross-filtering」** をON

または

**Dashboard Settings → Advanced**
- **「Enable dashboard cross filters」** にチェック

### 7. Dashboard Filter追加

#### 期間フィルター追加

1. Dashboard編集モード
2. 右側パネル **「Filters」** タブ
3. **「+ Add filter」**

**Filter設定**:
- Filter name: `期間`
- Filter type: `Time range`
- Dataset: `orders_with_status`
- Column: `order_date`
- Default value: `Last 30 days`

**Apply to charts**: 両方のChartを選択

**Save Dashboard**

---

## 動作確認

### テスト1: 期間フィルター

1. Dashboard を開く
2. 期間フィルターで「Last 7 days」を選択
3. **期待結果**: 円グラフに「新規」のみ表示される

### テスト2: Cross-Filter

1. 期間フィルターで「Last 30 days」を選択
2. 円グラフの「進行中」セグメントをクリック
3. **期待結果**: テーブルに「進行中」のデータのみ表示される

### テスト3: RLS（部署フィルター）

既存のGuest Token生成機能を使用：

```bash
curl "http://localhost:3001/api/superset/guest-token?departmentId=101"
```

**期待結果**: 部署101のデータのみ表示される

---

## RLS + Cross-Filter の組み合わせ

### SQL実行順序

```sql
-- 最終的に実行されるSQL（内部）
SELECT status, SUM(amount)
FROM (
    SELECT
        amount,
        CASE
            WHEN (CURRENT_DATE - order_date) < 7 THEN '新規'
            WHEN (CURRENT_DATE - order_date) < 30 THEN '進行中'
            ELSE '遅延'
        END AS status
    FROM orders
    WHERE department_id = 101  -- ★ RLS
      AND order_date >= '2024-01-01'  -- ★ Dashboard Filter
      AND order_date <= '2024-01-31'
) AS filtered_orders
WHERE status = '進行中'  -- ★ Cross-Filter（円グラフクリック）
GROUP BY status
```

### フィルタリングの優先順位

1. **RLS** - 常に適用（最優先）
2. **Dashboard Filter** - ユーザーが選択
3. **Cross-Filter** - Chartクリックで動的に追加

---

## トラブルシューティング

### Cross-Filterが動作しない

**原因**: Superset 5.0でCross-Filter機能が無効化されている可能性

**確認方法**:
```bash
docker exec superset_app grep -r "DASHBOARD_CROSS_FILTERS" /app/superset/
```

**対処法**:
Superset設定ファイル（`superset_config.py`）に追加：

```python
FEATURE_FLAGS = {
    "DASHBOARD_CROSS_FILTERS": True,
    "DASHBOARD_NATIVE_FILTERS": True,
}
```

### ステータスが更新されない

**原因**: Datasetのキャッシュが有効

**対処法**:
- Dataset設定 → Advanced → Cache Timeout: `0` (キャッシュ無効)
- または Dashboard → Refresh

---

## 次のステップ

1. ✅ サンプルデータ作成完了
2. ⬜ Superset UIでDataset作成
3. ⬜ Chart作成（円グラフ + テーブル）
4. ⬜ Dashboard作成
5. ⬜ Cross-Filter有効化
6. ⬜ 動作確認

実際にSuperset UIで設定しますか？それともスクリプトで自動化しますか？
