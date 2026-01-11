# GROUP BY前の動的フィルタリング - 実用的な解決策

## 問題の整理

1. **要求**: GROUP BYの前段階でdepartment_idでフィルタリングしたい
2. **制約**: Superset 5.0ではGuest TokenのextraフィールドをJinjaテンプレートから参照できない
3. **RLSの問題**: WHERE句が大外に適用されるため、GROUP BY後のフィルタリングになる

## 解決策の比較

### ❌ 実現不可能な方法
- `current_user().extra_json` - Guest userでは動作しない
- `get_guest_user_attribute()` - 未実装（提案段階）

### ✅ 実現可能な方法

---

## 方法1: 部署ごとにDashboard/Chartを分ける ⭐ **最も実用的**

### メリット
- ✅ シンプルで確実
- ✅ パフォーマンスが良い（事前にフィルタ済み）
- ✅ 部署ごとに異なるレイアウト/指標も設定可能
- ✅ 保守性が高い

### デメリット
- ⚠️ Dashboard/Chartの数が増える
- ⚠️ 共通の変更は複数箇所を更新する必要がある

### 実装方法

#### Step 1: 部署ごとのVirtual Datasetを作成

```sql
-- Dataset: sales_dept_101 (営業部)
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
WHERE s.department_id = 101  -- ★ GROUP BY前のフィルタ
ORDER BY s.sale_date DESC
```

```sql
-- Dataset: sales_dept_102 (開発部)
WHERE s.department_id = 102
```

```sql
-- Dataset: sales_dept_103 (マーケティング部)
WHERE s.department_id = 103
```

#### Step 2: 部署ごとのChartを作成

各DatasetをもとにChartを作成（例：部署別売上推移）

#### Step 3: 部署ごとのDashboardを作成または単一Dashboardに複数Chart配置

**オプションA**: 部署ごとに独立したDashboard
- Dashboard ID: 101 (営業部用)
- Dashboard ID: 102 (開発部用)
- Dashboard ID: 103 (マーケティング部用)

**オプションB**: 単一Dashboardに全Chartを配置し、Tabで切り替え

#### Step 4: Backend - Guest Token生成を変更

```typescript
// superset.service.ts
generateGuestToken(departmentId: number, username: string): string {
  // 部署に応じたDashboard UUIDをマッピング
  const dashboardMapping: Record<number, string> = {
    101: '7aaabc03-2c47-4540-8233-f22bbdb2cc81', // 営業部Dashboard UUID
    102: '8bbbcd04-3d58-5651-9344-g33ccec3dd92', // 開発部Dashboard UUID
    103: '9ccce05-4e69-6762-a455-h44ddfdf4ee03', // マーケティング部Dashboard UUID
  };

  const payload = {
    user: {
      username,
      first_name: 'Guest',
      last_name: 'User',
    },
    resources: [
      {
        type: 'dashboard',
        id: dashboardMapping[departmentId], // ★ 部署ごとに異なるDashboard
      },
    ],
    rls_rules: [], // 空でOK（既にDatasetでフィルタ済み）
    iat: now,
    exp: now + 86400,
    aud: 'http://superset:8088/',
    type: 'guest',
  };

  return jwt.sign(payload, this.SUPERSET_SECRET_KEY, { algorithm: 'HS256' });
}
```

#### Step 5: Frontend - 変更不要

Angularフロントエンドは既存のまま動作します。部署を切り替えると異なるDashboardが表示されます。

---

## 方法2: Chart Filter Boxを使用 ⚠️ **制約あり**

### 概要
Dashboard上にFilter BoxまたはNative Filterを配置し、ユーザーが手動で部署を選択する方法。

### メリット
- ✅ 単一のDashboard/Datasetで管理可能
- ✅ UIで直感的に操作可能

### デメリット
- ❌ **Guest Tokenでは動作しない**（Filter操作に認証が必要）
- ❌ ユーザーが手動で選択する必要がある（自動フィルタにならない）
- ❌ 他部署のデータも閲覧可能になる（セキュリティリスク）

### 結論
**Embedded環境では不適切** - この方法は諦める

---

## 方法3: Custom SQL per Chart（Chartごとにカスタムクエリ）

### 概要
同じDatasetを使うが、各Chartで「Custom SQL」を有効にしてWHERE句を追加する。

### Superset UIでの設定
1. Chart編集画面 → Advanced → "Custom SQL" を有効化
2. クエリに直接WHERE句を追加:
```sql
SELECT
    sale_date,
    SUM(amount) as total_amount
FROM sales_by_department
WHERE department_id = 101  -- ★ Chart固有のフィルタ
GROUP BY sale_date
```

### メリット
- ✅ Datasetは1つでOK
- ✅ GROUP BY前のフィルタリング可能

### デメリット
- ⚠️ Chartごとに異なるSQLを記述（保守コスト高）
- ⚠️ Datasetの変更がChartに自動反映されない
- ❌ 依然として部署ごとにChartが必要

### 結論
**方法1とほぼ同じ手間** - 方法1の方が管理しやすい

---

## 方法4: Database Viewを使用

### 概要
PostgreSQL側で部署ごとのViewを作成し、SupersetからはそのViewを参照する。

```sql
-- PostgreSQLで実行
CREATE VIEW sales_dept_101 AS
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
WHERE s.department_id = 101;

CREATE VIEW sales_dept_102 AS ...;
CREATE VIEW sales_dept_103 AS ...;
```

### Supersetでの設定
- 各ViewをPhysical Datasetとして登録
- Chartを作成

### メリット
- ✅ DB層で管理（Superset外でも利用可能）
- ✅ パフォーマンスが良い（Materialized Viewも可能）
- ✅ セキュリティが堅牢

### デメリット
- ⚠️ DBスキーマ変更が必要
- ⚠️ View数が増える

### 結論
**本番環境向け** - Superset Virtual Datasetと同等だが、DB側で管理したい場合に有効

---

## 推奨実装: 方法1の詳細手順

### Supersetでの作業

#### 1. 部署ごとのVirtual Dataset作成

**SQL Lab → SQL Editor**

```sql
-- Dataset 1: sales_dept_101
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
WHERE s.department_id = 101
ORDER BY s.sale_date DESC
```

**「Save」→「Save as Dataset」→ Dataset名: `sales_dept_101`**

同様に `sales_dept_102`, `sales_dept_103` を作成。

#### 2. 部署ごとのChartを作成

**Charts → + Create Chart**

- Dataset: `sales_dept_101`
- Chart Type: `Time-series Line Chart`
- Time Column: `sale_date`
- Metric: `SUM(amount)`
- Title: `営業部 売上推移`

同様に開発部、マーケティング部のChartを作成。

#### 3. Dashboardを作成

**オプションA: 単一Dashboardに全Chart配置**

新しいDashboard「部署別売上ダッシュボード」を作成し、3つのChartをTabで切り替え表示。

**オプションB: 部署ごとに独立したDashboard**

- Dashboard「営業部ダッシュボード」→ Chart `sales_dept_101`
- Dashboard「開発部ダッシュボード」→ Chart `sales_dept_102`
- Dashboard「マーケティング部ダッシュボード」→ Chart `sales_dept_103`

#### 4. Embedded Dashboardとして公開

各DashboardのSettings → Advanced → **"Embedding"を有効化**

**Embedded Dashboard UUIDを取得**（Backend設定で使用）

---

### Backend実装（オプションA: 単一Dashboard + Tab切り替え）

単一Dashboardに全Chartがある場合、Guest Tokenは1つでOK。Angularフロントエンド側で見せるだけ。

```typescript
// 変更なし - 既存の実装でOK
generateGuestToken(departmentId: number, username: string): string {
  const payload = {
    user: { username, first_name: 'Guest', last_name: 'User' },
    resources: [
      { type: 'dashboard', id: this.EMBEDDED_DASHBOARD_UUID }
    ],
    rls_rules: [],
    iat: now,
    exp: now + 86400,
    aud: 'http://superset:8088/',
    type: 'guest',
  };
  return jwt.sign(payload, this.SUPERSET_SECRET_KEY, { algorithm: 'HS256' });
}
```

**ただし**: Superset Dashboardのタブ機能はEmbedded環境では制限があるため、次のオプションBを推奨。

---

### Backend実装（オプションB: 部署ごとに独立Dashboard） ⭐ **推奨**

```typescript
// superset.service.ts
private readonly DASHBOARD_UUIDS: Record<number, string> = {
  101: '7aaabc03-2c47-4540-8233-f22bbdb2cc81', // 営業部
  102: '8bbbcd04-3d58-5651-9344-g33ccec3dd92', // 開発部
  103: '9ccce05-4e69-6762-a455-h44ddfdf4ee03', // マーケティング部
};

generateGuestToken(departmentId: number, username: string): string {
  const dashboardUuid = this.DASHBOARD_UUIDS[departmentId];

  if (!dashboardUuid) {
    throw new Error(`No dashboard configured for department ${departmentId}`);
  }

  const now = Math.floor(Date.now() / 1000);
  const payload = {
    user: {
      username,
      first_name: 'Guest',
      last_name: 'User',
    },
    resources: [
      {
        type: 'dashboard',
        id: dashboardUuid, // ★ 部署ごとに異なるDashboard
      },
    ],
    rls_rules: [],
    iat: now,
    exp: now + 86400,
    aud: 'http://superset:8088/',
    type: 'guest',
  };

  return jwt.sign(payload, this.SUPERSET_SECRET_KEY, { algorithm: 'HS256' });
}

getDashboardUrl(guestToken: string, departmentId: number): string {
  const dashboardUuid = this.DASHBOARD_UUIDS[departmentId];
  return `${this.SUPERSET_URL}/dashboard/embedded/${dashboardUuid}`;
}
```

### Controller更新

```typescript
// superset.controller.ts
@Get('guest-token')
getGuestToken(
  @Query('departmentId') departmentId: string,
  @Query('username') username: string,
) {
  const deptId = parseInt(departmentId, 10);
  const user = username || `部署${deptId}ユーザー`;

  const token = this.supersetService.generateGuestToken(deptId, user);
  const dashboardUrl = this.supersetService.getDashboardUrl(token, deptId);

  return {
    token,
    dashboardUrl,
    departmentId: deptId,
    username: user,
  };
}
```

---

### Frontend実装の変更

```typescript
// dashboard.component.ts
async loadDepartment(department: Department) {
  this.selectedDepartment = department;

  // 省略: unmount処理

  try {
    const response = await this.http.get<GuestTokenResponse>(
      `http://localhost:3001/api/superset/guest-token?departmentId=${department.id}`
    ).toPromise();

    if (!response) {
      throw new Error('Failed to get guest token');
    }

    console.log('Loading dashboard for', department.name);
    console.log('Dashboard URL:', response.dashboardUrl);

    // ★ response.dashboardUrl に部署ごとのDashboard UUIDが含まれる
    // Embedded SDKは自動的に正しいDashboardを読み込む

    this.currentEmbed = await embedDashboard({
      id: this.extractUuidFromUrl(response.dashboardUrl), // URLからUUIDを抽出
      supersetDomain: 'http://localhost:8088',
      mountPoint: container!,
      fetchGuestToken: async () => response.token,
      dashboardUiConfig: {
        hideTitle: false,
        hideChartControls: false,
        hideTab: false,
      },
    });

    console.log('Dashboard loaded:', department.name);
  } catch (error) {
    console.error('Failed to embed dashboard:', error);
  }
}

// Helper method
private extractUuidFromUrl(url: string): string {
  const match = url.match(/embedded\/([a-f0-9-]+)/);
  return match ? match[1] : this.EMBEDDED_DASHBOARD_UUID; // Fallback
}
```

---

## まとめ

### 現実的な解決策

**方法1（部署ごとにDashboard分ける）が最も確実でメンテナンス性も高い**

#### 作業手順
1. ✅ Superset: 部署ごとのVirtual Dataset作成（WHERE department_id = XXX）
2. ✅ Superset: 部署ごとのChart作成
3. ✅ Superset: 部署ごとのDashboard作成 & Embedding有効化
4. ✅ Backend: Dashboard UUID マッピング実装
5. ✅ Frontend: 既存のコードでほぼ動作（UUID抽出ロジック追加のみ）

#### メリット
- ✅ GROUP BY前のフィルタリングが確実に動作
- ✅ パフォーマンスが良い
- ✅ セキュリティが堅牢（部署間のデータ漏洩なし）
- ✅ 部署ごとにカスタマイズ可能

#### デメリット
- ⚠️ Dashboard/Chart数が増える
- ⚠️ 共通の変更は複数箇所を更新

### 将来的な改善

Superset 6.x以降で `get_guest_user_attribute()` が実装されれば、単一Dashboard/Datasetで動的フィルタリングが可能になります。その際は移行を検討してください。

---

**検証日**: 2026-01-11
**対象バージョン**: Superset 5.0.0
