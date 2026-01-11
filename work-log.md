# Superset v5.0 動的フィルタリング検証 - 作業ログ

## 目的
現在の案件で使用している Superset v5.0 で、Dataset Extra JSON + Jinja Template による動的フィルタリングが正しく動作するかを検証する

## 制約条件
- ✅ Superset のソースコードは変更しない
- ✅ Docker 設定の変更は可能
- ✅ 使用イメージ: `docker-compose-image-tag.yml` で指定されたイメージ
- ✅ ベースブランチ: v5.0

## 環境情報
- Superset リポジトリ: `/Users/kazu/coding/research-superset/superset`
- Docker Compose ファイル: `docker-compose-image-tag.yml`
- 設定ファイル: `docker/pythonpath_dev/superset_config.py`
- 環境変数: `docker/.env`
- SECRET_KEY: `TEST_NON_DEV_SECRET` (開発用)

## 実装ステップ

### Phase 1: 環境構築
- [ ] Docker Compose で Superset を起動
- [ ] サンプルデータの確認 (SUPERSET_LOAD_EXAMPLES=yes が設定済み)
- [ ] Admin ログイン確認

### Phase 2: サンプルデータセットの作成
- [ ] PostgreSQL にカスタムテーブル作成 (departments, users, sales)
- [ ] Superset で Database 接続確認
- [ ] Virtual Dataset 作成 (sales_by_department)

### Phase 3: Dataset Extra JSON 設定
- [ ] Dataset に Extra JSON 追加
- [ ] Jinja Template 設定 (`where` 句)
- [ ] SQL Lab で動作確認

### Phase 4: RLS (Row Level Security) 設定
- [ ] RLS Rule 作成
- [ ] Guest Token 用の clause 設定
- [ ] 動作確認

### Phase 5: チャート・ダッシュボード作成
- [ ] Bar Chart 作成
- [ ] Dashboard 作成
- [ ] Dashboard UUID 取得

### Phase 6: Guest Token 生成スクリプト
- [ ] Python スクリプト作成
- [ ] PyJWT インストール
- [ ] Token 生成テスト

### Phase 7: 動作検証
- [ ] 部署ID 101 のフィルタ動作確認
- [ ] 部署ID 102 のフィルタ動作確認
- [ ] SQL Lab でクエリ確認

### Phase 8: 設定の最適化
- [ ] superset_config.py に Guest Token 設定追加
- [ ] CORS 設定 (必要に応じて)
- [ ] セキュリティ設定確認

---

## 現在の状態

### 確認済み
- ✅ docker-compose-image-tag.yml を確認
- ✅ docker/.env を確認
- ✅ superset_config.py を確認
- ✅ SECRET_KEY: `TEST_NON_DEV_SECRET`
- ✅ PostgreSQL 使用 (db サービス)
- ✅ SUPERSET_LOAD_EXAMPLES=yes (サンプルデータあり)

### 次のアクション
1. Docker Compose で Superset を起動
2. Admin でログイン (初期ユーザー確認)
3. サンプルデータの状態確認

---

## メモ

### superset_config.py の重要な設定
- `SQLALCHEMY_DATABASE_URI`: PostgreSQL 接続 (superset DB)
- `SQLALCHEMY_EXAMPLES_URI`: Examples DB (サンプルデータ用)
- `FEATURE_FLAGS`: 機能フラグ設定
- `superset_config_docker.py` を読み込み可能 (カスタム設定用)

### Guest Token に必要な設定 (後で追加)
```python
GUEST_TOKEN_JWT_SECRET = SECRET_KEY
GUEST_TOKEN_JWT_ALGO = "HS256"
GUEST_TOKEN_JWT_EXP_SECONDS = 86400
```

### カスタムテーブル用 SQL (後で実行)
```sql
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    department_name VARCHAR(100),
    region VARCHAR(50)
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    department_id INTEGER REFERENCES departments(id),
    status VARCHAR(20)
);

CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    sale_date DATE,
    amount DECIMAL(10, 2),
    department_id INTEGER REFERENCES departments(id),
    product_name VARCHAR(100)
);
```

---

## 進捗状況
- **現在のフェーズ**: Phase 1 (環境構築)
- **進捗**: 0/8 フェーズ完了
