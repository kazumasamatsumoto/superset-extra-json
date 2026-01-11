# Superset 5.0 Jinjaテンプレート詳細調査レポート

**調査日**: 2026-01-11
**Superset Version**: 5.0.0
**調査範囲**: Guest Token使用時のJinjaテンプレート変数アクセス

---

## エグゼクティブサマリー

### 主要な発見

1. **Guest TokenでJinjaテンプレートから`extra_json`が読み込めない根本原因を特定**
   - `GuestUser`クラスに`id`属性が存在しない
   - `current_user_id()`が`None`を返すことで、多くのユーザー固有情報へのアクセスが制限される

2. **利用可能なJinja変数・関数を完全にリスト化**
   - Guest Tokenで動作するマクロ: 9個
   - Guest Tokenで動作しないマクロ: 2個

3. **回避策を3つ提示**
   - `username`ベースのフィルタリング
   - RLS (Row Level Security)の活用
   - URLパラメータの利用

---

## 1. なぜGuest Tokenで`extra_json`が読み込めないのか

### 根本原因

**`GuestUser`クラスに`id`属性が定義されていないため**

### 技術的詳細

#### 1.1 GuestUserクラスの構造

**ファイル**: `superset/security/guest_token.py:56-89`

```python
class GuestUser(AnonymousUserMixin):
    """
    Used as the "anonymous" user in case of guest authentication (embedded)
    """

    is_guest_user = True

    def __init__(self, token: GuestToken, roles: list[Role]):
        user = token["user"]
        self.guest_token = token
        self.username = user.get("username", "guest_user")
        self.first_name = user.get("first_name", "Guest")
        self.last_name = user.get("last_name", "User")
        self.roles = roles
        self.resources = token["resources"]
        self.rls = token.get("rls_rules", [])
        # ⚠️ self.id は定義されていない
        # ⚠️ self.email も定義されていない
```

**重要**: `id`属性が存在しないため、`g.user.id`にアクセスすると`AttributeError`が発生します。

#### 1.2 ユーザーID取得関数の実装

**ファイル**: `superset/utils/core.py:1262-1277`

```python
def get_user_id() -> int | None:
    """
    Get the user identifier (if defined) associated with the current user.
    """
    try:
        return g.user.id  # ← GuestUserには.idが存在しない
    except Exception:  # pylint: disable=broad-except
        return None  # 例外発生時はNoneを返す
```

**動作**:
- **Regular User**: `g.user.id`が存在 → ユーザーIDを返す
- **Guest User**: `g.user.id`が存在しない → 例外が発生 → `None`を返す

#### 1.3 Jinjaコンテキストでの影響

**ファイル**: `superset/jinja_context.py:133-145`

```python
def current_user_id(self, add_to_cache_keys: bool = True) -> Optional[int]:
    """
    Return the user ID of the user who is currently logged in.
    """
    if user_id := get_user_id():  # ← Guest Userの場合はNone
        if add_to_cache_keys:
            self.cache_key_wrapper(user_id)
        return user_id
    return None  # Guest Userは常にここに到達
```

**結果**: `{{ current_user_id() }}`はGuest Tokenでは常に`None`を返す

### なぜ設計上`id`を持たないのか

**理由**: セキュリティとプライバシー保護

- Guest Userはデータベースに永続化されない一時的なユーザー
- ユーザーIDが存在すると、データベース上のユーザーテーブルと紐付けられる
- Guest Tokenベースの認証では、トークン内の情報のみで完結させる設計

---

## 2. Guest TokenとRegular Userの違い

### 2.1 オブジェクト構造の比較

| 属性 | Regular User (Flask-AppBuilder) | Guest User | アクセス方法 |
|------|--------------------------------|------------|--------------|
| **id** | ✅ あり (整数型) | ❌ なし | `g.user.id` |
| **username** | ✅ あり | ✅ あり (tokenから) | `g.user.username` |
| **first_name** | ✅ あり | ✅ あり (tokenから) | `g.user.first_name` |
| **last_name** | ✅ あり | ✅ あり (tokenから) | `g.user.last_name` |
| **email** | ✅ あり | ❌ なし | `g.user.email` |
| **roles** | ✅ あり (DBから) | ✅ あり (tokenから動的生成) | `g.user.roles` |
| **is_authenticated** | ✅ True | ✅ True | `g.user.is_authenticated` |
| **is_anonymous** | ❌ False | ❌ False | `g.user.is_anonymous` |
| **is_guest_user** | ❌ 属性なし | ✅ True | `g.user.is_guest_user` |
| **guest_token** | ❌ なし | ✅ あり (完全なトークン) | `g.user.guest_token` |
| **resources** | ❌ なし | ✅ あり (アクセス可能リソース) | `g.user.resources` |
| **rls** | ❌ なし | ✅ あり (RLSルール) | `g.user.rls` |

### 2.2 Guest Tokenの構造

**ファイル**: `superset/security/guest_token.py:48-53`

```python
class GuestToken(TypedDict):
    iat: float                              # 発行時刻 (UNIX timestamp)
    exp: float                              # 有効期限 (UNIX timestamp)
    user: GuestTokenUser                    # ユーザー情報
    resources: GuestTokenResources          # アクセス可能なリソース
    rls_rules: list[GuestTokenRlsRule]     # Row Level Securityルール
```

**重要な発見**: Guest Tokenの`TypedDict`定義には`extra_json`フィールドが存在しません。

つまり、以下のようなGuest Token:

```json
{
  "user": {
    "username": "test_user",
    "first_name": "Guest",
    "last_name": "User",
    "extra_json": {
      "target_department_id": 101
    }
  },
  "resources": [...],
  "rls_rules": [...]
}
```

この`extra_json`フィールドは、Superset 5.0の型定義では**サポートされていない非標準フィールド**です。

### 2.3 Jinjaコンテキスト構築の違い

両方とも同じ`JinjaContext`クラスを使用しますが、実行時の値が異なります。

**ファイル**: `superset/jinja_context.py:640-691`

```python
def set_context(self, **kwargs: Any) -> None:
    super().set_context(**kwargs)
    extra_cache = ExtraCache(...)

    self._context.update({
        "url_param": partial(safe_proxy, extra_cache.url_param),
        "current_user_id": partial(safe_proxy, extra_cache.current_user_id),
        "current_username": partial(safe_proxy, extra_cache.current_username),
        "current_user_email": partial(safe_proxy, extra_cache.current_user_email),
        "cache_key_wrapper": partial(safe_proxy, extra_cache.cache_key_wrapper),
        "filter_values": partial(safe_proxy, extra_cache.filter_values),
        "get_filters": partial(safe_proxy, extra_cache.get_filters),
        "dataset": partial(safe_proxy, dataset_macro_with_context),
        "get_time_filter": partial(safe_proxy, extra_cache.get_time_filter),
    })
```

**実行時の違い**:

| マクロ | Regular User | Guest User |
|--------|--------------|------------|
| `current_user_id()` | 実際のユーザーID (例: 42) | `None` |
| `current_username()` | ユーザー名 (例: "admin") | トークンから取得 (例: "guest_user") |
| `current_user_email()` | メールアドレス | `None` |
| `url_param()` | 動作する | 動作する |
| `filter_values()` | 動作する | 動作する |

---

## 3. 現在利用可能なJinja変数・関数の完全リスト

### 3.1 ユーザー関連マクロ

#### `{{ current_user_id(add_to_cache_keys=True) }}`

- **説明**: 現在ログインしているユーザーのID
- **戻り値**: `int | None`
- **Guest User**: ❌ **常に`None`を返す**
- **Regular User**: ✅ ユーザーIDを返す
- **実装**: `superset/jinja_context.py:133-145`

**サンプル**:
```sql
SELECT * FROM orders
WHERE user_id = {{ current_user_id() }}
-- Guest User: WHERE user_id = NULL (動作しない)
```

---

#### `{{ current_username(add_to_cache_keys=True) }}`

- **説明**: 現在ログインしているユーザーのユーザー名
- **戻り値**: `str | None`
- **Guest User**: ✅ **トークンから取得した`username`を返す**
- **Regular User**: ✅ ユーザー名を返す
- **実装**: `superset/jinja_context.py:147-156`

**サンプル**:
```sql
SELECT * FROM logs
WHERE username = '{{ current_username() }}'
-- Guest User: WHERE username = 'guest_user' (動作する)
```

---

#### `{{ current_user_email(add_to_cache_keys=True) }}`

- **説明**: 現在ログインしているユーザーのメールアドレス
- **戻り値**: `str | None`
- **Guest User**: ❌ **常に`None`を返す**
- **Regular User**: ✅ メールアドレスを返す
- **実装**: `superset/jinja_context.py:158-167`

**サンプル**:
```sql
SELECT * FROM notifications
WHERE email = '{{ current_user_email() }}'
-- Guest User: WHERE email = NULL (動作しない)
```

---

### 3.2 URLパラメータマクロ

#### `{{ url_param('param_name', default=None, add_to_cache_keys=True, escape_result=True) }}`

- **説明**: URLクエリパラメータまたは`form_data`から値を取得
- **戻り値**: `str | None`
- **Guest User**: ✅ **動作する**
- **Regular User**: ✅ 動作する
- **実装**: `superset/jinja_context.py:169-210`

**サンプル**:
```sql
-- URL: /sqllab?country=US
SELECT * FROM sales
WHERE country_code = '{{ url_param('country', 'UNKNOWN') }}'
-- 結果: WHERE country_code = 'US'
```

**重要**: `escape_result=True`（デフォルト）の場合、SQLインジェクション対策のためエスケープされます。

---

### 3.3 フィルター関連マクロ

#### `{{ filter_values('column_name', default=None, remove_filter=False) }}`

- **説明**: 特定のカラムに適用されたフィルター値をリストで取得
- **戻り値**: `list[Any]`
- **Guest User**: ✅ **動作する**
- **Regular User**: ✅ 動作する
- **実装**: `superset/jinja_context.py:225-252`

**サンプル**:
```sql
SELECT action, count(*) as times
FROM logs
WHERE action IN {{ filter_values('action_type', ['default'])|where_in }}
GROUP BY action
```

**使用例**:
- フィルターで "view", "click", "purchase" を選択
- `filter_values('action_type')` → `['view', 'click', 'purchase']`
- `|where_in` フィルター適用 → `('view', 'click', 'purchase')`

---

#### `{{ get_filters('column_name', remove_filter=False) }}`

- **説明**: 特定のカラムに適用されたフィルターをオペレータ付きで取得
- **戻り値**: `list[Filter]` where `Filter = {op: str, col: str, val: Any}`
- **Guest User**: ✅ **動作する**
- **Regular User**: ✅ 動作する
- **実装**: `superset/jinja_context.py:212-223`

**サンプル**:
```sql
WHERE 1=1
{%- for filter in get_filters('full_name', remove_filter=True) -%}
  {%- if filter.get('op') == 'IN' -%}
    AND full_name IN {{ filter.get('val')|where_in }}
  {%- elif filter.get('op') == 'LIKE' -%}
    AND full_name LIKE '{{ filter.get('val') }}'
  {%- endif -%}
{%- endfor -%}
```

**フィルターオペレータの例**:
- `IN`: リスト値
- `LIKE`: パターンマッチ
- `==`: 等価
- `>=`, `<=`: 比較

---

#### `{{ get_time_filter(column=None, default=None, target_type=None, strftime=None, remove_filter=False) }}`

- **説明**: 時間フィルターを取得
- **戻り値**: `TimeFilter` (属性: `from_expr`, `to_expr`, `time_range`)
- **Guest User**: ✅ **動作する**
- **Regular User**: ✅ 動作する
- **実装**: `superset/jinja_context.py:254-311`

**サンプル**:
```sql
{% set time_filter = get_time_filter("dttm", remove_filter=True) %}
SELECT *
FROM logs
WHERE dttm >= {{ time_filter.from_expr }}
  AND dttm < {{ time_filter.to_expr }}
```

**パラメータ説明**:
- `column`: 時間カラム名（Noneの場合はデフォルトの時間カラム）
- `target_type`: 出力型（例: `'TIMESTAMP'`, `'DATE'`）
- `strftime`: 日付フォーマット（例: `'%Y-%m-%d'`）
- `remove_filter`: `True`の場合、このフィルターをクエリから除外

---

### 3.4 データセット・メトリックマクロ

#### `{{ dataset(dataset_id, include_metrics=False, columns=None) }}`

- **説明**: データセットをサブクエリとして取得
- **戻り値**: `str` (SQL文字列)
- **Guest User**: ✅ **動作する**（ただしRLS制限が適用される）
- **Regular User**: ✅ 動作する
- **実装**: `superset/jinja_context.py:457-550`

**サンプル**:
```sql
-- 基本的な使用法
SELECT * FROM {{ dataset(42) }} LIMIT 10

-- メトリックを含める
SELECT * FROM {{ dataset(42, include_metrics=True) }}

-- 特定のカラムのみ
SELECT * FROM {{ dataset(42, columns=["ds", "category", "revenue"]) }}
```

**重要**: Guest Userの場合、`rls_rules`が適用されるため、アクセスできるデータが制限されます。

---

#### `{{ metric('metric_name', dataset_id=None) }}`

- **説明**: メトリックのSQL式を取得
- **戻り値**: `str` (SQL式)
- **Guest User**: ✅ **動作する**
- **Regular User**: ✅ 動作する
- **実装**: `superset/jinja_context.py:583-616`

**サンプル**:
```sql
SELECT
  category,
  {{ metric('revenue') }} as total_revenue,
  {{ metric('count') }} as order_count
FROM sales
GROUP BY category
```

**注意**: メトリック名が見つからない場合は例外が発生します。

---

### 3.5 キャッシュ関連マクロ

#### `{{ cache_key_wrapper(value) }}`

- **説明**: キャッシュキーに値を明示的に追加
- **戻り値**: `Any` (渡された値をそのまま返す)
- **Guest User**: ✅ **動作する**
- **Regular User**: ✅ 動作する
- **実装**: `superset/jinja_context.py:87-96`

**サンプル**:
```sql
{% set custom_value = 'US' %}
SELECT * FROM data
WHERE region = '{{ cache_key_wrapper(custom_value) }}'
```

**目的**: カスタム変数をキャッシュキーに含めることで、値が変わった際にキャッシュを無効化

---

### 3.6 Jinja2組み込みフィルター

#### `|where_in`

- **説明**: リストをIN句用の文字列に変換
- **Guest User**: ✅ **動作する**
- **Regular User**: ✅ 動作する
- **実装**: `superset/jinja_context.py:617-623`

**サンプル**:
```sql
WHERE country IN {{ ['US', 'UK', 'JP']|where_in }}
-- 結果: WHERE country IN ('US', 'UK', 'JP')

WHERE status IN {{ filter_values('status')|where_in }}
-- フィルター値が ['active', 'pending'] の場合
-- 結果: WHERE status IN ('active', 'pending')
```

---

### 3.7 コンテキスト変数

以下の変数は`kwargs`として渡されます（Chart設定から）:

| 変数名 | 説明 | タイプ | 非推奨 |
|--------|------|--------|--------|
| `columns` | グループ化するカラム | `list[str]` | - |
| `filter` | 適用されたフィルター | `list[dict]` | - |
| `from_dttm` | 開始日時 | `datetime` | ✅ 5.0以降 |
| `to_dttm` | 終了日時 | `datetime` | ✅ 5.0以降 |
| `groupby` | グループ化カラム（古い名前） | `list[str]` | ✅ 非推奨 |
| `metrics` | メトリック式 | `list[str]` | - |
| `row_limit` | 行数制限 | `int` | - |
| `row_offset` | オフセット | `int` | - |
| `table_columns` | テーブルカラム | `list[str]` | - |
| `time_column` | 時間カラム | `str` | - |
| `time_grain` | 時間粒度 | `str` | - |

**サンプル**:
```sql
SELECT
  {{ columns|join(', ') }},
  count(*) as cnt
FROM my_table
GROUP BY {{ columns|join(', ') }}
LIMIT {{ row_limit }}
```

---

### 3.8 カスタムアドオン (`JINJA_CONTEXT_ADDONS`)

`superset_config.py`で独自の関数を追加可能:

```python
def get_fiscal_year(date_col):
    return f"CASE WHEN MONTH({date_col}) >= 4 THEN YEAR({date_col}) ELSE YEAR({date_col}) - 1 END"

JINJA_CONTEXT_ADDONS = {
    'fiscal_year': get_fiscal_year,
    'company_name': lambda: 'ACME Corp',
}
```

**使用例**:
```sql
SELECT
  {{ fiscal_year('order_date') }} as fy,
  '{{ company_name() }}' as company,
  sum(amount) as revenue
FROM sales
GROUP BY {{ fiscal_year('order_date') }}
```

---

## 4. Guest Token使用時の制限事項まとめ

### ❌ 動作しないマクロ

| マクロ | 理由 | 代替手段 |
|--------|------|----------|
| `{{ current_user_id() }}` | `GuestUser.id`が存在しない | `{{ current_username() }}`を使用 |
| `{{ current_user_email() }}` | `GuestUser.email`が存在しない | URLパラメータまたはRLS |

### ✅ 動作するマクロ

| マクロ | Guest Userでの動作 |
|--------|-------------------|
| `{{ current_username() }}` | トークンから取得 |
| `{{ url_param() }}` | 完全に動作 |
| `{{ filter_values() }}` | 完全に動作 |
| `{{ get_filters() }}` | 完全に動作 |
| `{{ get_time_filter() }}` | 完全に動作 |
| `{{ dataset() }}` | 動作（RLS制限あり） |
| `{{ metric() }}` | 完全に動作 |
| `{{ cache_key_wrapper() }}` | 完全に動作 |
| `\|where_in` | 完全に動作 |

---

## 5. Guest Tokenで個別化されたクエリを実現する回避策

### 方法1: `username`を使用

**適用ケース**: ユーザーごとにデータを分離したい場合

```sql
SELECT * FROM user_data
WHERE username = '{{ current_username() }}'
```

**Guest Token設定**:
```json
{
  "user": {
    "username": "customer_12345"
  }
}
```

**利点**:
- ✅ シンプル
- ✅ Jinjaテンプレートで完結

**欠点**:
- ❌ ユーザー名が推測可能な場合セキュリティリスク
- ❌ `username`フィールドを別の目的で使えない

---

### 方法2: RLS (Row Level Security)を使用

**適用ケース**: セキュアなデータフィルタリングが必要な場合

**Guest Token設定**:
```json
{
  "user": {
    "username": "guest_user"
  },
  "rls_rules": [
    {
      "dataset": "sales_data",
      "clause": "department_id = 101"
    },
    {
      "dataset": "orders",
      "clause": "region = 'US'"
    }
  ]
}
```

**利点**:
- ✅ セキュア（Superset内部でWHERE句を強制）
- ✅ Dataset単位で細かく制御可能
- ✅ SQLテンプレート不要

**欠点**:
- ❌ WHERE句が大外に適用される（GROUP BY後のフィルタリングになる）
- ❌ 複雑な条件式は書きにくい

---

### 方法3: URLパラメータを使用

**適用ケース**: フロントエンドから動的にパラメータを渡したい場合

**SQLクエリ**:
```sql
SELECT * FROM orders
WHERE customer_id = {{ url_param('customer_id', 0) }}
  AND status = '{{ url_param('status', 'all') }}'
```

**呼び出し**:
```typescript
const dashboardUrl = `http://localhost:8088/superset/dashboard/1/?customer_id=123&status=active`;
```

**利点**:
- ✅ 柔軟性が高い
- ✅ フロントエンド側で制御可能

**欠点**:
- ❌ URLが長くなる
- ❌ セキュリティリスク（URLからパラメータが見える）
- ❌ ブックマークや共有時に注意が必要

---

### 方法4: 複数Datasetを使用（最も確実）

**適用ケース**: 部署ごとに完全に異なるデータを表示したい場合

**実装**:
1. 部署ごとにDatasetを作成
   - `sales_dept_101` (department_id = 101)
   - `sales_dept_102` (department_id = 102)

2. 部署ごとにDashboardを作成
   - Dashboard 1: sales_dept_101を使用
   - Dashboard 2: sales_dept_102を使用

3. Guest Tokenで適切なDashboardを指定
```json
{
  "resources": [
    {
      "type": "dashboard",
      "id": "dashboard_uuid_for_dept_101"
    }
  ]
}
```

**利点**:
- ✅ 完全に分離されたデータ
- ✅ セキュア
- ✅ Jinjaテンプレート不要

**欠点**:
- ❌ 管理コストが高い（部署数分のDataset/Dashboardが必要）
- ❌ スケールしにくい

---

## 6. なぜ`extra_json`が提案されたのか

### GitHub Discussionの背景

[Discussion #33918](https://github.com/apache/superset/discussions/33918)と[SIP-174](https://github.com/apache/superset/issues/33922)で提案されている機能:

```python
# 提案されている理想的な実装
guest_token = {
    "user": {
        "username": "external_user",
        "attributes": {  # ← 新しいフィールド
            "tenant_id": "company_123",
            "department_id": 101,
            "region": "us-west"
        }
    }
}
```

```sql
-- Jinjaテンプレートでアクセス（提案中）
SELECT * FROM sales_data
WHERE tenant_id = '{{ get_guest_user_attribute("tenant_id") }}'
  AND department_id = {{ get_guest_user_attribute("department_id") }}
```

### まだ実装されていない理由

1. **セキュリティ検証が必要**
   - Guest Tokenから任意の属性にアクセスできると、情報漏洩のリスク
   - キャッシュキーへの影響を慎重に検討する必要がある

2. **後方互換性**
   - 既存のGuest Token実装を壊さない設計が必要

3. **実装の複雑さ**
   - `GuestUser`クラスと`ExtraCache`クラスの両方を修正する必要がある
   - 型定義（`TypedDict`）の更新が必要

---

## 7. 参照ファイルパス

調査で使用した主要なソースファイル:

| ファイル | 内容 |
|---------|------|
| `superset/jinja_context.py` | Jinjaコンテキストの実装 |
| `superset/security/guest_token.py` | Guest Token型定義 |
| `superset/utils/core.py` | ユーザー情報取得関数 |
| `superset/docs/docs/configuration/sql-templating.mdx` | 公式ドキュメント |
| `tests/unit_tests/jinja_context_test.py` | テストコード |

---

## 8. 結論

### 調査で判明した事実

1. **`extra_json`が読み込めない理由**:
   - Guest Tokenの`TypedDict`定義に`extra_json`フィールドが存在しない
   - `GuestUser`クラスに`id`属性が存在せず、`current_user_id()`が`None`を返す
   - Jinjaテンプレートから`g.user.guest_token["user"]["extra_json"]`に直接アクセスする手段がない

2. **現在利用可能なマクロ**:
   - Guest Tokenで動作: 9個
   - Guest Tokenで動作しない: 2個

3. **推奨される回避策**:
   - `username`ベースのフィルタリング（シンプルなケース）
   - RLS (Row Level Security)（セキュアなケース）
   - URLパラメータ（動的なケース）
   - 複数Dataset（完全分離が必要なケース）

### 今後の展望

Apache Supersetコミュニティで`get_guest_user_attribute()`マクロの実装が議論されています。この機能が実装されれば、Guest Tokenから任意の属性にアクセスできるようになり、現在の制限が解消される見込みです。

**監視すべきリソース**:
- [GitHub Discussion #33918](https://github.com/apache/superset/discussions/33918)
- [GitHub Issue #33922 (SIP-174)](https://github.com/apache/superset/issues/33922)
- [Superset Release Notes](https://github.com/apache/superset/releases)

---

**調査完了日**: 2026-01-11
**調査者**: Claude Code (Anthropic)
**Superset Version**: 5.0.0
