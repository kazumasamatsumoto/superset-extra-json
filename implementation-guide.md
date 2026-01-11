# Superset 動的フィルタリング実装ガイド

## 何を実装するのか？

**Guest Token を使った埋め込みダッシュボードで、ユーザーごとに異なるデータを表示する仕組み**を実装します。

### 実現すること
- ユーザーA がダッシュボードを開く → 部署A のデータのみ表示
- ユーザーB がダッシュボードを開く → 部署B のデータのみ表示
- 同じダッシュボード・同じチャートを使い回しながら、**動的にフィルタを適用**

### 使用する技術
- **Dataset Extra JSON**: データセットレベルでのフィルタ定義
- **Jinja Template**: 動的な値の埋め込み
- **Guest Token**: 認証不要の埋め込みURL生成
- **RLS (Row Level Security)**: 行レベルのセキュリティ制御

---

## 実装手順

### 前提条件
- Superset がインストール済み
- データベース接続が設定済み
- サンプルデータが用意されている

---

## ステップ1: サンプルデータの準備

### 1-1. テーブル作成 (PostgreSQL例)

```sql
-- 部署マスタ
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    department_name VARCHAR(100),
    region VARCHAR(50)
);

-- ユーザーマスタ
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    department_id INTEGER REFERENCES departments(id),
    status VARCHAR(20)
);

-- 売上データ
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    sale_date DATE,
    amount DECIMAL(10, 2),
    department_id INTEGER REFERENCES departments(id),
    product_name VARCHAR(100)
);
```

### 1-2. サンプルデータ投入

```sql
-- 部署データ
INSERT INTO departments (id, department_name, region) VALUES
(101, '営業部', '東京'),
(102, '開発部', '大阪'),
(103, 'マーケティング部', '東京');

-- ユーザーデータ
INSERT INTO users (id, name, email, department_id, status) VALUES
(1, '田中太郎', 'tanaka@example.com', 101, 'active'),
(2, '佐藤花子', 'sato@example.com', 102, 'active'),
(3, '鈴木一郎', 'suzuki@example.com', 103, 'active');

-- 売上データ
INSERT INTO sales (sale_date, amount, department_id, product_name) VALUES
('2024-01-15', 150000, 101, '商品A'),
('2024-01-16', 280000, 102, '商品B'),
('2024-01-17', 95000, 103, '商品C'),
('2024-01-18', 320000, 101, '商品A'),
('2024-01-19', 175000, 102, '商品D');
```

---

## ステップ2: Superset でのデータベース接続

### 2-1. Database 登録

Superset UI で:
1. **Settings** → **Database Connections** → **+ Database**
2. **SUPPORTED DATABASES** から PostgreSQL を選択
3. 接続情報を入力:
   ```
   Host: localhost
   Port: 5432
   Database name: your_database
   Username: your_username
   Password: your_password
   ```
4. **CONNECT** をクリック

---

## ステップ3: Dataset の作成と設定

### 3-1. Virtual Dataset の作成

1. **SQL Lab** を開く
2. 以下のSQLを実行:

```sql
-- Dataset名: sales_by_department
SELECT
    s.id,
    s.sale_date,
    s.amount,
    s.product_name,
    s.department_id,
    d.department_name,
    d.region
FROM sales s
LEFT JOIN departments d ON s.department_id = d.id
ORDER BY s.sale_date DESC
```

3. クエリ実行後、**SAVE** → **Save dataset** をクリック
4. Dataset名: `sales_by_department` と入力して保存

### 3-2. Dataset の Extra JSON 設定

1. **Data** → **Datasets** から `sales_by_department` を選択
2. 右上の **Edit** をクリック
3. **Advanced** タブを開く
4. **Extra** フィールドに以下を入力:

```json
{
  "where": "department_id = {{ current_user_id()|default(0) }}"
}
```

5. **Save** をクリック

### 3-2 (応用). 複数条件の場合

```json
{
  "where": "department_id = {{ current_user_id()|default(0) }} AND region = '{{ current_username()|default('unknown') }}'"
}
```

---

## ステップ4: チャートの作成

### 4-1. 基本的なチャート作成

1. **Charts** → **+ Chart**
2. **Choose a dataset**: `sales_by_department` を選択
3. **Choose chart type**: Bar Chart を選択
4. **CREATE NEW CHART** をクリック

### 4-2. チャート設定

**DATA** タブ:
- **DIMENSIONS**: `sale_date`
- **METRICS**: `SUM(amount)`
- **FILTERS**: (なし - Extra JSON で自動適用される)

**CUSTOMIZE** タブ:
- **Chart Title**: 部署別売上推移
- 他は任意で調整

5. **UPDATE CHART** → **SAVE** をクリック

---

## ステップ5: ダッシュボードの作成

### 5-1. Dashboard 作成

1. **Dashboards** → **+ Dashboard**
2. **Title**: 部署別売上ダッシュボード
3. 作成したチャートをドラッグ&ドロップ
4. **SAVE** をクリック

### 5-2. Dashboard UUID の取得

ダッシュボードを開いた状態で、URLから UUID を取得:
```
http://localhost:8088/superset/dashboard/12345/
                                         ↑
                                    この番号をメモ
```

または、ブラウザの開発者ツールで:
```javascript
// コンソールで実行
window.location.pathname.split('/')[3]
```

---

## ステップ6: Guest Token の生成

### 6-1. Python スクリプト作成

`generate_guest_token.py` を作成:

```python
import jwt
import datetime
import sys

# Superset の設定
SUPERSET_SECRET_KEY = "your-secret-key-from-superset-config"  # 要変更
SUPERSET_URL = "http://localhost:8088"
DASHBOARD_ID = "your-dashboard-id"  # ステップ5-2で取得したID

def generate_guest_token(department_id, username):
    """
    Guest Token を生成

    Args:
        department_id: 部署ID (current_user_id として使用される)
        username: ユーザー名 (current_username として使用される)
    """
    payload = {
        "user": {
            "username": username,
            "first_name": "Guest",
            "last_name": "User"
        },
        "resources": [{
            "type": "dashboard",
            "id": DASHBOARD_ID
        }],
        "rls": [
            {"clause": f"department_id = {department_id}"}
        ],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }

    token = jwt.encode(payload, SUPERSET_SECRET_KEY, algorithm="HS256")
    embed_url = f"{SUPERSET_URL}/guest/{token}/"

    return token, embed_url

if __name__ == "__main__":
    # 使用例
    departments = [
        (101, "営業部ユーザー"),
        (102, "開発部ユーザー"),
        (103, "マーケティング部ユーザー")
    ]

    print("=== Guest Token 生成 ===\n")

    for dept_id, user_name in departments:
        token, url = generate_guest_token(dept_id, user_name)
        print(f"部署ID: {dept_id}")
        print(f"ユーザー名: {user_name}")
        print(f"Token: {token}")
        print(f"URL: {url}")
        print("-" * 80)
        print()
```

### 6-2. 必要なライブラリのインストール

```bash
pip install PyJWT
```

### 6-3. SECRET_KEY の取得

Superset の設定ファイルから取得:

```bash
# Superset がインストールされているディレクトリで
grep SECRET_KEY superset_config.py
```

または、Python で確認:

```python
from superset import app
print(app.config['SECRET_KEY'])
```

### 6-4. スクリプト実行

```bash
python generate_guest_token.py
```

出力例:
```
=== Guest Token 生成 ===

部署ID: 101
ユーザー名: 営業部ユーザー
Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
URL: http://localhost:8088/guest/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.../
--------------------------------------------------------------------------------

部署ID: 102
ユーザー名: 開発部ユーザー
Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
URL: http://localhost:8088/guest/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.../
--------------------------------------------------------------------------------
```

---

## ステップ7: 動作確認

### 7-1. ブラウザでテスト

1. 生成された URL をブラウザで開く
2. **部署ID 101 のURL**: 営業部のデータのみ表示されることを確認
3. **部署ID 102 のURL**: 開発部のデータのみ表示されることを確認

### 7-2. SQL Lab で確認

実際に生成されているクエリを確認:

1. **SQL Lab** を開く
2. 以下のクエリを実行:

```sql
-- Extra JSON が適用されたクエリ (概念的)
SELECT * FROM (
    SELECT
        s.id,
        s.sale_date,
        s.amount,
        s.product_name,
        s.department_id,
        d.department_name,
        d.region
    FROM sales s
    LEFT JOIN departments d ON s.department_id = d.id
) AS virtual_table
WHERE department_id = 101  -- Extra JSON から適用
  AND department_id = 101  -- RLS clause から適用 (重複)
```

---

## ステップ8: 本番環境への適用

### 8-1. セキュリティ設定

`superset_config.py` に以下を追加:

```python
# Guest Token の有効化
GUEST_TOKEN_JWT_SECRET = SECRET_KEY
GUEST_TOKEN_JWT_ALGO = "HS256"
GUEST_TOKEN_JWT_EXP_SECONDS = 86400  # 24時間

# CORS設定 (埋め込み先ドメインを指定)
ENABLE_CORS = True
CORS_OPTIONS = {
    'supports_credentials': True,
    'allow_headers': ['*'],
    'resources': ['*'],
    'origins': ['https://your-app-domain.com']
}
```

### 8-2. HTTPS 対応

本番環境では必ず HTTPS を使用:

```python
# superset_config.py
ENABLE_PROXY_FIX = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'None'
```

---

## ステップ9: アプリケーションへの埋め込み

### 9-1. HTML 埋め込み例

```html
<!DOCTYPE html>
<html>
<head>
    <title>埋め込みダッシュボード</title>
    <style>
        iframe {
            width: 100%;
            height: 800px;
            border: none;
        }
    </style>
</head>
<body>
    <h1>部署別売上ダッシュボード</h1>
    <iframe
        src="http://localhost:8088/guest/YOUR_GUEST_TOKEN/"
        allow="camera; microphone; fullscreen; display-capture">
    </iframe>
</body>
</html>
```

### 9-2. React 埋め込み例

```javascript
import React, { useState, useEffect } from 'react';

function SupersetDashboard({ departmentId, username }) {
  const [guestUrl, setGuestUrl] = useState('');

  useEffect(() => {
    // バックエンドAPIからGuest Tokenを取得
    fetch('/api/generate-guest-token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ departmentId, username })
    })
      .then(res => res.json())
      .then(data => setGuestUrl(data.url));
  }, [departmentId, username]);

  return (
    <div>
      <h2>ダッシュボード</h2>
      {guestUrl && (
        <iframe
          src={guestUrl}
          width="100%"
          height="800px"
          frameBorder="0"
        />
      )}
    </div>
  );
}

export default SupersetDashboard;
```

### 9-3. バックエンドAPI例 (Flask)

```python
from flask import Flask, request, jsonify
import jwt
import datetime

app = Flask(__name__)

SUPERSET_SECRET_KEY = "your-secret-key"
SUPERSET_URL = "http://localhost:8088"
DASHBOARD_ID = "your-dashboard-id"

@app.route('/api/generate-guest-token', methods=['POST'])
def generate_token():
    data = request.json
    department_id = data.get('departmentId')
    username = data.get('username')

    payload = {
        "user": {
            "username": username,
            "first_name": "Guest",
            "last_name": "User"
        },
        "resources": [{
            "type": "dashboard",
            "id": DASHBOARD_ID
        }],
        "rls": [
            {"clause": f"department_id = {department_id}"}
        ],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }

    token = jwt.encode(payload, SUPERSET_SECRET_KEY, algorithm="HS256")
    url = f"{SUPERSET_URL}/guest/{token}/"

    return jsonify({"url": url, "token": token})

if __name__ == '__main__':
    app.run(debug=True)
```

---

## トラブルシューティング

### 問題1: フィルタが適用されない

**確認ポイント**:
1. Dataset の Extra JSON が正しく保存されているか
2. RLS clause の構文が正しいか
3. Guest Token の `rls` 配列が正しく設定されているか

**デバッグ方法**:
```sql
-- SQL Lab で手動実行
SELECT * FROM sales_by_department
WHERE department_id = 101
```

### 問題2: Guest Token が Invalid

**確認ポイント**:
1. SECRET_KEY が正しいか
2. Token の有効期限が切れていないか
3. DASHBOARD_ID が正しいか

**デバッグ方法**:
```python
import jwt

token = "your-token"
secret = "your-secret-key"

try:
    decoded = jwt.decode(token, secret, algorithms=["HS256"])
    print(decoded)
except jwt.ExpiredSignatureError:
    print("Token has expired")
except jwt.InvalidTokenError:
    print("Invalid token")
```

### 問題3: CORS エラー

**確認ポイント**:
1. `superset_config.py` で CORS が有効化されているか
2. `origins` に埋め込み先ドメインが含まれているか

**解決方法**:
```python
# superset_config.py
ENABLE_CORS = True
CORS_OPTIONS = {
    'supports_credentials': True,
    'allow_headers': ['*'],
    'resources': ['*'],
    'origins': ['http://localhost:3000', 'https://your-domain.com']
}
```

---

## まとめ

この実装により、以下が実現されます:

| 機能 | 実装方法 |
|------|---------|
| **動的フィルタリング** | Dataset Extra JSON + Jinja |
| **認証不要アクセス** | Guest Token |
| **行レベルセキュリティ** | RLS clause |
| **アプリケーション埋め込み** | iframe + バックエンドAPI |

### 重要なポイント
1. **Extra JSON の `where` 句**が最も重要な設定
2. **Guest Token の `rls` 配列**で動的に値を渡す
3. **Jinja 関数** (`current_user_id()` など) で値を取得
4. **本番環境では HTTPS 必須**

### 次のステップ
- [ ] 複数のフィルタ条件を追加
- [ ] Token の有効期限管理
- [ ] キャッシュ戦略の最適化
- [ ] パフォーマンスモニタリング
