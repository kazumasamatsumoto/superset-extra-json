# Supersetの動的フィルタリング - 推奨アプローチまとめ

## 概要

Supersetで動的なデータフィルタリング(特にGuest Tokenを使った埋め込みダッシュボード)を実装する際の、**仕様に最も適した推奨アプローチ**をまとめます。

---

## 基本原理: クエリのラップ構造

SupersetのRLS clauseやGuest Tokenフィルタは、元のクエリを**サブクエリとしてラップ**する形で適用されます。

### 物理的な構造
```sql
-- 適用前のクエリ
SELECT * FROM users WHERE status = 'active'

-- RLS/フィルタ適用後
SELECT * FROM (
  SELECT * FROM users WHERE status = 'active'
) AS virtual_table
WHERE department_id = 123  -- RLS clause または Guest Token フィルタ
```

この構造により、**元のクエリの結果セットに対して追加の WHERE 句が適用される**ことになります。

---

## 推奨アプローチ 1: Dataset Extra JSON + Jinja Template

### メリット
- ✅ **セキュリティ**: SQLインジェクションのリスクが低い
- ✅ **動的**: Guest Token payloadで値を渡せる
- ✅ **Supersetのセキュリティモデルと整合性がある**
- ✅ **メンテナンス性**: データセット設定で一元管理

### 実装手順

#### 1. Dataset の Extra JSON 設定
```json
{
  "where": "department_id = {{ current_user_id()|default(0) }}"
}
```

または複数条件:
```json
{
  "where": "department_id = {{ current_user_id()|default(0) }} AND region = '{{ current_username()|default('unknown') }}'"
}
```

#### 2. Guest Token での値渡し
```python
# Python例
guest_token_payload = {
    "user": {
        "username": "user@example.com",
        "first_name": "John",
        "last_name": "Doe"
    },
    "resources": [{
        "type": "dashboard",
        "id": "dashboard-uuid"
    }],
    "rls": [
        {"clause": "department_id = 123"}
    ]
}
```

#### 3. 生成されるクエリ
```sql
SELECT * FROM (
  SELECT * FROM users
) AS virtual_table
WHERE department_id = 123  -- Extra JSONから生成
  AND department_id = 123  -- RLS clauseから(重複する場合)
```

### 注意点
- `current_user_id()` や `current_username()` はSupersetのJinja関数
- Guest Tokenの場合、これらの値は **Guest Token payload** から取得される
- `|default(0)` はフォールバック値の設定

---

## 推奨アプローチ 2: Virtual Dataset (Custom SQL) + RLS

### メリット
- ✅ **柔軟性**: 複雑なビジネスロジックをSQLで実装可能
- ✅ **再利用性**: Virtual Datasetを複数のチャートで共有可能
- ✅ **パフォーマンス最適化**: 必要なデータだけを事前に絞り込める

### 実装手順

#### 1. Virtual Dataset の作成
```sql
-- Virtual Dataset SQL (例: user_department_data)
SELECT
    u.id,
    u.name,
    u.email,
    d.department_name,
    d.region,
    u.department_id
FROM users u
JOIN departments d ON u.department_id = d.id
WHERE u.status = 'active'
```

#### 2. RLS Rule の設定
Supersetの管理画面で:
- **Name**: Department Filter
- **Tables**: user_department_data
- **Clause**: `department_id = {{ current_user_id() }}`
- **Group Key**: (オプション) キャッシュキー

#### 3. Guest Token での適用
```python
guest_token_payload = {
    "user": {
        "username": "department_123",  # この値がcurrent_username()で取得される
        "first_name": "Dept",
        "last_name": "123"
    },
    "resources": [{
        "type": "dashboard",
        "id": "dashboard-uuid"
    }],
    "rls": [
        {"clause": "department_id = 123"}
    ]
}
```

#### 4. 最終的なクエリ
```sql
SELECT * FROM (
  SELECT
      u.id,
      u.name,
      u.email,
      d.department_name,
      d.region,
      u.department_id
  FROM users u
  JOIN departments d ON u.department_id = d.id
  WHERE u.status = 'active'
) AS virtual_table
WHERE department_id = 123  -- RLS clauseから適用
```

---

## 推奨アプローチ 3: Database Extra JSON (Presto/Trino)

### メリット
- ✅ **データベースレベルでの制御**: 全データセットに一律適用可能
- ✅ **一元管理**: Database設定で管理

### 適用対象
- **Presto/Trino** などのクエリエンジン
- **BigQuery** (一部対応)

### 実装手順

#### 1. Database の Extra JSON 設定
```json
{
  "engine_params": {
    "connect_args": {
      "session_properties": {
        "current_department": "123"
      }
    }
  }
}
```

#### 2. データセット側での利用
```sql
-- Virtual DatasetまたはSQL Lab
SELECT * FROM users
WHERE department_id = CAST('{{ current_department }}' AS INTEGER)
```

### 注意点
- データベースエンジンによって対応状況が異なる
- PostgreSQL/MySQL では直接的なサポートが限定的

---

## アプローチの選択基準

| ユースケース | 推奨アプローチ | 理由 |
|---|---|---|
| **Guest Token埋め込み** | アプローチ1 (Extra JSON + Jinja) | Guest Token payloadとの統合が容易 |
| **複雑なフィルタロジック** | アプローチ2 (Virtual Dataset + RLS) | SQLで柔軟にビジネスロジックを実装可能 |
| **全データセット統一制御** | アプローチ3 (Database Extra JSON) | 一元管理が可能(対応DB限定) |
| **マルチテナント** | アプローチ1 + 2の併用 | RLSで基本制御 + Extra JSONで詳細制御 |

---

## 検証用サンプルコード

### 1. Guest Token生成 (Python)
```python
import jwt
import datetime

# Supersetの設定
SUPERSET_SECRET_KEY = "your-secret-key"  # superset_config.py の SECRET_KEY
DASHBOARD_ID = "dashboard-uuid"

# Payload
payload = {
    "user": {
        "username": "guest_user_dept_123",
        "first_name": "Guest",
        "last_name": "User"
    },
    "resources": [{
        "type": "dashboard",
        "id": DASHBOARD_ID
    }],
    "rls": [
        {"clause": "department_id = 123"}
    ],
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
}

# トークン生成
token = jwt.encode(payload, SUPERSET_SECRET_KEY, algorithm="HS256")
print(f"Guest Token: {token}")

# 埋め込みURL
embed_url = f"http://localhost:8088/guest/{token}/{DASHBOARD_ID}"
print(f"Embed URL: {embed_url}")
```

### 2. Dataset Extra JSON (テスト用)
```json
{
  "where": "department_id = {{ current_user_id()|default(999) }}",
  "certification": {
    "certified_by": "Data Team",
    "details": "Filtered by department"
  }
}
```

### 3. Virtual Dataset SQL (テスト用)
```sql
-- Dataset名: filtered_sales
SELECT
    s.id,
    s.sale_date,
    s.amount,
    s.department_id,
    d.department_name
FROM sales s
LEFT JOIN departments d ON s.department_id = d.id
WHERE s.sale_date >= DATE '2024-01-01'
```

### 4. RLS Rule 設定 (SQL Lab で検証)
```sql
-- RLS適用後のクエリをSQL Labで確認
SELECT * FROM filtered_sales
-- Supersetが自動的に以下を追加:
-- WHERE department_id = 123
```

---

## トラブルシューティング

### 1. フィルタが適用されない
- ✅ Dataset の Extra JSON が正しく設定されているか確認
- ✅ RLS Rule が有効化されているか確認
- ✅ Guest Token の `rls` 配列が正しく設定されているか確認

### 2. SQLエラーが発生
- ✅ Jinja構文が正しいか確認 (`{{ }}` の記法)
- ✅ データ型の不一致がないか確認 (文字列 vs 数値)
- ✅ SQL Lab で手動実行してクエリを検証

### 3. パフォーマンス問題
- ✅ Virtual Dataset に適切なインデックスが設定されているか確認
- ✅ RLS clause が複雑すぎないか確認
- ✅ データベース側のクエリログで実行計画を確認

---

## まとめ

| 項目 | 内容 |
|---|---|
| **基本原理** | クエリのサブクエリ化 + 外側WHERE句追加 |
| **最推奨** | Dataset Extra JSON + Jinja Template |
| **セキュリティ** | RLS clause でバックエンド制御 |
| **動的値の渡し方** | Guest Token payload → Jinja関数 |
| **検証方法** | SQL Lab + Guest Token URL テスト |

この構造を理解すれば、Supersetの動的フィルタリングの仕様に沿った実装が可能になります。
