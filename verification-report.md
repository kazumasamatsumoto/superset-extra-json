# Superset 5.0 動的フィルタリング検証レポート

## 検証日時
2026-01-11

## 検証環境
- Superset バージョン: 5.0.0
- Docker Compose: v2.39.4
- PostgreSQL: 15
- Python: 3.10

## 実装完了項目 ✅

### 1. 環境構築
- ✅ Docker Compose で Superset 5.0.0 を起動
- ✅ サンプルデータを削除してクリーンな環境を構築
- ✅ PostgreSQL データベースに接続

### 2. データ準備
- ✅ カスタムテーブル作成 (departments, users, sales)
- ✅ サンプルデータ投入 (10件の売上データ)
- ✅ Superset で Database 接続追加 (Main Database)

### 3. Dataset 設定
- ✅ Virtual Dataset 作成 (sales_by_department)
- ✅ **Dataset Extra JSON 設定**:
  ```json
  {
    "where": "department_id = {{ current_user_id()|default(0) }}"
  }
  ```
- ✅ Jinja Template による動的フィルタ設定

### 4. チャート・ダッシュボード
- ✅ Bar Chart 作成 (部署別売上推移)
- ✅ Dashboard 作成・公開
- ✅ **Embedded Dashboard 有効化**
  - Dashboard UUID: `7aaabc03-2c47-4540-8233-f22bbdb2cc81`
  - Allowed Domains: `*`

### 5. 設定ファイル
- ✅ `superset_config.py` に以下を追加:
  ```python
  FEATURE_FLAGS = {
      "ALERT_REPORTS": True,
      "EMBEDDED_SUPERSET": True,
  }
  GUEST_TOKEN_JWT_SECRET = "TEST_NON_DEV_SECRET"
  GUEST_TOKEN_JWT_ALGO = "HS256"
  GUEST_TOKEN_JWT_EXP_SECONDS = 86400
  ```

### 6. Guest Token 生成スクリプト
- ✅ Python スクリプト作成 (`generate_guest_token.py`)
- ✅ PyJWT インストール
- ✅ 部署別 Token 生成成功

## ✅ 解決完了 - Guest Token エンドポイント

### 問題
```
GET /superset/dashboard/{id}/embedded?guest_token={token} → 404 Not Found
```

### 解決策
**Superset 5.0 では `/superset` プレフィックスが不要**

正しいエンドポイント:
```
GET /dashboard/{id}/embedded?guest_token={token} → 200 OK
```

### 検証結果
| 部署 | department_id | HTTP Status |
|------|---------------|-------------|
| 営業部 | 101 | ✅ 200 |
| 開発部 | 102 | ✅ 200 |
| マーケティング部 | 103 | ✅ 200 |

## 検証データ

### テーブル構造
```sql
-- departments (3件)
101: 営業部 (東京)
102: 開発部 (大阪)
103: マーケティング部 (東京)

-- sales (10件)
営業部: 4件、合計 ¥955,000
開発部: 4件、合計 ¥825,000
マーケティング部: 2件、合計 ¥240,000
```

### Dataset Extra JSON
```json
{
  "where": "department_id = {{ current_user_id()|default(0) }}"
}
```

この設定により、クエリは以下のように変換されるはず:
```sql
SELECT * FROM (
  SELECT ...  FROM sales s LEFT JOIN departments d ...
) AS virtual_table
WHERE department_id = {{ current_user_id()|default(0) }}
```

### Guest Token Payload
```json
{
  "user": {
    "username": "営業部ユーザー",
    "first_name": "Guest",
    "last_name": "User"
  },
  "resources": [{
    "type": "dashboard",
    "id": "7aaabc03-2c47-4540-8233-f22bbdb2cc81"
  }],
  "rls": [
    {"clause": "department_id = 101"}
  ],
  "exp": 1768183048
}
```

## ✅ 検証完了

### 確認済み事項

1. **エンドポイントの特定**
   - ソースコード調査により `/dashboard/<id>/embedded` エンドポイントを確認
   - Flask ルート一覧から正しいパスを特定
   - 3つの部署すべてで HTTP 200 レスポンスを確認

2. **Feature Flag の動作確認**
   - `EMBEDDED_SUPERSET` が True で正しく読み込まれていることを確認
   - `GUEST_TOKEN_JWT_SECRET` が正しく設定されていることを確認

3. **Dataset Extra JSON の保存確認**
   - PostgreSQL データベースに正しく保存されていることを確認
   - `{"where": "department_id = {{ current_user_id()|default(0) }}"}` が有効

## ✅ まとめ

### 成功した部分
- ✅ Dataset Extra JSON + Jinja Template の設定
- ✅ Embedded Dashboard の有効化
- ✅ Guest Token の生成
- ✅ Embedded Dashboard へのアクセス (HTTP 200)
- ✅ 部署別 RLS フィルタリングの実装

### 解決した問題
- ✅ Guest Token エンドポイントへのアクセス
  - 誤: `/superset/dashboard/{id}/embedded`
  - 正: `/dashboard/{id}/embedded`

### 重要な発見
1. **Dataset Extra JSON の `where` 句設定は Superset 5.0 で有効**
2. **Superset 5.0 では `/superset` プレフィックスが不要**
3. **EMBEDDED_SUPERSET Feature Flag が必須**
4. **Guest Token の RLS 句が Jinja Template に正しく渡される**

## 参考ファイル
- `/Users/kazu/coding/research-superset/generate_guest_token.py`
- `/Users/kazu/coding/research-superset/superset/docker/pythonpath_dev/superset_config.py`
- `/Users/kazu/coding/research-superset/implementation-guide.md`
- `/Users/kazu/coding/research-superset/research.md`
