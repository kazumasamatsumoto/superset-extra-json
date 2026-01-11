# Superset 5.0 動的フィルタリング検証結果

## 検証内容

Dataset Extra JSON + Jinja Template + Guest Token の `extra_json` を使用して、GROUP BY の前段階でフィルタリングができるかを検証しました。

## 結論: ❌ **Superset 5.0 では実現不可能**

### 検証で判明した事実

1. **Jinja テンプレートから guest token の属性にアクセスする機能は未実装**
   - `current_user().extra_json.target_department_id` → Guest ユーザーでは動作しない
   - `get_guest_user_attribute()` → 提案中の機能だが未実装
   - `guest_token_template_variable()` → 提案中の機能だが未実装

2. **Guest Token の構造**
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
     "rls_rules": [],
     "iat": ...,
     "exp": ...,
     "aud": "http://superset:8088/",
     "type": "guest"
   }
   ```
   - `extra_json` フィールドは Guest Token に含めることができる
   - **しかし、Jinja テンプレートからアクセスする方法が存在しない**

3. **Dataset Extra JSON の設定**
   ```json
   {
     "where": "department_id = {{ current_user().extra_json.target_department_id|default(0) }}"
   }
   ```
   - この設定は保存できる
   - **しかし、Guest ユーザーの場合は評価されない（synthetic context のため）**

4. **現時点で利用可能な動的フィルタリング手法**
   - **RLS (Row Level Security) のみ**
   - Guest Token に `rls_rules` を含める:
     ```json
     {
       "rls_rules": [
         {
           "clause": "department_id = 101"
         }
       ]
     }
     ```
   - **問題点**: RLS は WHERE 句を大外（GROUP BY の後）に適用するため、集計前のフィルタリングができない

## Apache Superset の今後の改善提案

以下の提案が GitHub で議論されていますが、まだ実装されていません:

### 1. [Discussion #33918](https://github.com/apache/superset/discussions/33918)
**提案**: `guest_token_template_variable("key")` マクロの追加

```sql
SELECT * FROM my_table
WHERE tenant_id = '{{ guest_token_template_variable("tenant_id") }}'
```

### 2. [SIP-174 - Issue #33922](https://github.com/apache/superset/issues/33922)
**提案**: `get_guest_user_attribute(attribute_name, default=None)` マクロの追加

```python
# Guest Token 生成時
guest_token = security_manager.create_guest_access_token(
    user={
        "username": "external_user",
        "attributes": {
            "tenant_id": "company_123",
            "region": "us-west"
        }
    }
)
```

```sql
-- SQL クエリ内
SELECT * FROM sales_data
WHERE tenant_id = '{{ get_guest_user_attribute("tenant_id") }}'
```

## 検証環境

- **Superset**: 5.0.0
- **Backend**: Nest.js 10.x + TypeScript
- **Frontend**: Angular 21.x
- **Embedded SDK**: @superset-ui/embedded-sdk 0.3.0

## 検証で実装した内容

### 1. Guest Token 生成 (Backend)
- ✅ `rls_rules: []` と `extra_json` を両方含める（認証に必要）
- ✅ Department ID を `extra_json.target_department_id` に格納
- ✅ JWT の必須フィールド: `iat`, `exp`, `aud`, `type`

### 2. Dataset Extra JSON 設定 (Superset)
```sql
UPDATE tables
SET extra = '{"where": "department_id = {{ current_user().extra_json.target_department_id|default(0) }}"}'
WHERE table_name = 'sales_by_department';
```

### 3. Angular フロントエンド
- ✅ 部署ごとのタブ表示
- ✅ タブ切り替え時に新しい Guest Token を取得
- ✅ Superset Embedded SDK で Dashboard を埋め込み

## 確認された動作

1. **認証**: ✅ 401エラーなし（`rls_rules: []` を含めることで解決）
2. **Dashboard 表示**: ✅ 正常に表示
3. **動的フィルタリング**: ❌ **全ての部署で同じデータが表示される**

## スクリーンショット比較

以下の3つのスクリーンショットを確認した結果、すべて同じチャートが表示されている:
- `test-extra-json-営業部.png` (ID: 101, 期待値: ¥955,000)
- `test-extra-json-開発部.png` (ID: 102, 期待値: ¥835,000)
- `test-extra-json-マーケティング部.png` (ID: 103, 期待値: ¥240,000)

→ **フィルタリングが機能していないことを確認**

## 代替案

現時点での唯一の解決策は、集計ロジックを変更することです:

### オプション 1: ビューを使用
```sql
-- 各部署用のビューを作成
CREATE VIEW sales_dept_101 AS
SELECT * FROM sales_data WHERE department_id = 101;

CREATE VIEW sales_dept_102 AS
SELECT * FROM sales_data WHERE department_id = 102;
```
- 各部署に異なる Dataset/Chart を作成
- Guest Token の `resources` で適切な Dashboard を指定

### オプション 2: Virtual Dataset
```sql
-- Dataset の SQL を直接記述
SELECT
  date,
  department_id,
  amount
FROM sales_data
WHERE department_id = 101  -- 固定値
```
- 部署ごとに別々の Dataset を作成
- 柔軟性は低い

### オプション 3: 将来の Superset バージョンを待つ
- SIP-174 の実装を待つ
- Superset のリリースノートを確認: https://github.com/apache/superset/releases

## 参考資料

- [Apache Superset Documentation - SQL Templating](https://superset.apache.org/docs/configuration/sql-templating/)
- [GitHub Discussion #33918 - New Jinja Macro for Guest Token Variables](https://github.com/apache/superset/discussions/33918)
- [GitHub Issue #33922 - SIP-174 Guest User Attributes](https://github.com/apache/superset/issues/33922)
- [Superset Embedded SDK README](https://github.com/apache/superset/blob/master/superset-embedded-sdk/README.md)

---

**検証日**: 2026-01-11
**検証者**: Claude Code (Anthropic)
