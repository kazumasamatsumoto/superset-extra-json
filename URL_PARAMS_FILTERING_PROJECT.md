# Superset URL Parameters フィルタリング プロジェクト

**目的**: URL Parametersを使用してGuest Token環境でJinjaテンプレートによる動的フィルタリングを実現する

**技術スタック**:
- Frontend: Angular v20 + Superset Embedded SDK
- Backend: Nest.js v11
- BI Tool: Apache Superset 5.0

---

## プロジェクト構成

```
superset-urlparams-demo/
├── backend/                    # Nest.js v11
│   ├── src/
│   │   ├── app.module.ts
│   │   ├── superset/
│   │   │   ├── superset.controller.ts
│   │   │   ├── superset.service.ts
│   │   │   └── dto/
│   │   │       └── guest-token.dto.ts
│   │   └── main.ts
│   ├── package.json
│   └── tsconfig.json
├── frontend/                   # Angular v20
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/
│   │   │   │   └── dashboard/
│   │   │   │       ├── dashboard.component.ts
│   │   │   │       ├── dashboard.component.html
│   │   │   │       └── dashboard.component.css
│   │   │   ├── services/
│   │   │   │   └── superset.service.ts
│   │   │   └── app.component.ts
│   │   └── index.html
│   ├── package.json
│   └── angular.json
└── README.md
```

---

## セットアップ手順

### 1. Superset環境構築

#### 1.1 Docker ComposeでSuperset起動

```bash
# Supersetリポジトリをクローン
git clone https://github.com/apache/superset.git
cd superset

# Docker環境起動
TAG=5.0.0 docker compose -f docker-compose-image-tag.yml up -d

# 初期化完了を待つ（数分かかる）
docker compose logs -f superset_app
```

#### 1.2 サンプルデータ作成

**SQL**: `setup_sample_data.sql`

```sql
-- 部署マスタ
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    region VARCHAR(50)
);

INSERT INTO departments (id, name, region) VALUES
(101, '営業部', 'Tokyo'),
(102, '開発部', 'Osaka'),
(103, 'マーケティング部', 'Tokyo');

-- 売上データ
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    sale_date DATE NOT NULL,
    department_id INT NOT NULL,
    product_name VARCHAR(100),
    amount DECIMAL(10, 2),
    quantity INT,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

-- サンプルデータ投入
INSERT INTO sales (sale_date, department_id, product_name, amount, quantity) VALUES
-- 営業部 (101)
('2024-01-15', 101, '製品A', 50000, 5),
('2024-01-20', 101, '製品B', 30000, 3),
('2024-02-10', 101, '製品A', 45000, 4),
('2024-02-25', 101, '製品C', 60000, 6),

-- 開発部 (102)
('2024-01-10', 102, '製品X', 80000, 8),
('2024-01-28', 102, '製品Y', 25000, 2),
('2024-02-05', 102, '製品X', 90000, 9),
('2024-02-20', 102, '製品Z', 40000, 4),

-- マーケティング部 (103)
('2024-01-12', 103, '製品P', 15000, 1),
('2024-01-25', 103, '製品Q', 20000, 2),
('2024-02-08', 103, '製品P', 18000, 1),
('2024-02-22', 103, '製品R', 22000, 2);

-- データ確認
SELECT
    d.name as department,
    COUNT(*) as sales_count,
    SUM(s.amount) as total_amount
FROM sales s
JOIN departments d ON s.department_id = d.id
GROUP BY d.name
ORDER BY d.name;
```

**実行**:
```bash
docker exec -i superset_db psql -U superset -d superset < setup_sample_data.sql
```

#### 1.3 Virtual Dataset作成（Jinjaテンプレート使用）

**Superset UI操作**:

1. **Data → Datasets → + Dataset**
2. **Create Dataset from SQL** を選択
3. **Dataset Name**: `sales_by_department_filtered`
4. **SQL**:

```sql
SELECT
    s.sale_date,
    s.department_id,
    d.name as department_name,
    d.region,
    s.product_name,
    s.amount,
    s.quantity
FROM sales s
JOIN departments d ON s.department_id = d.id
WHERE s.department_id = {{ url_param('department_id', 0)|int }}
ORDER BY s.sale_date DESC
```

**重要ポイント**:
- `{{ url_param('department_id', 0)|int }}` - URL/form_dataから`department_id`を取得
- `|int` フィルター - 文字列を整数に変換（SQLインジェクション対策）
- デフォルト値 `0` - パラメータがない場合は0（該当データなし）

5. **Save**

#### 1.4 Chart作成

1. **Charts → + Chart**
2. **Dataset**: `sales_by_department_filtered`
3. **Chart Type**: Table または Pie Chart
4. **Configuration**:
   - Table: すべてのカラムを表示
   - Pie Chart: Dimension=`product_name`, Metric=`SUM(amount)`
5. **Save**

#### 1.5 Dashboard作成

1. **Dashboards → + Dashboard**
2. **Title**: `部署別売上分析（URLパラメータフィルタリング）`
3. 作成したChartをドラッグ&ドロップ
4. **Save**
5. **Dashboard UUID をコピー** (URLから取得)

#### 1.6 Embedded設定とGuest Role作成

**SQL**:
```sql
-- Guestロールの権限確認
SELECT * FROM ab_role WHERE name = 'Guest';

-- Embedded設定の有効化（superset_config.py）
-- FEATURE_FLAGS = {
--     "EMBEDDED_SUPERSET": True,
--     "DASHBOARD_NATIVE_FILTERS": True,
--     "DASHBOARD_CROSS_FILTERS": True,
-- }
```

または Superset UI:
1. **Settings → Feature Flags**
2. **EMBEDDED_SUPERSET**: ON

---

### 2. Backend (Nest.js v11)

#### 2.1 プロジェクト作成

```bash
mkdir superset-urlparams-demo
cd superset-urlparams-demo

# Nest.js CLIインストール
npm i -g @nestjs/cli

# プロジェクト作成
nest new backend
cd backend

# 必要なパッケージインストール
npm install jsonwebtoken
npm install -D @types/jsonwebtoken
```

#### 2.2 環境変数設定

**`.env`**:
```env
# Superset設定
SUPERSET_URL=http://localhost:8088
SUPERSET_SECRET_KEY=YOUR_SECRET_KEY_FROM_SUPERSET_CONFIG
DASHBOARD_UUID=your-dashboard-uuid-here

# Server設定
PORT=3001
FRONTEND_URL=http://localhost:4200
```

**SECRET_KEY取得方法**:
```bash
# Supersetコンテナ内で確認
docker exec superset_app cat /app/pythonpath/superset_config.py | grep SECRET_KEY
```

#### 2.3 Guest Token生成サービス

**`src/superset/superset.service.ts`**:

```typescript
import { Injectable } from '@nestjs/common';
import * as jwt from 'jsonwebtoken';

@Injectable()
export class SupersetService {
  private readonly SUPERSET_SECRET_KEY = process.env.SUPERSET_SECRET_KEY;
  private readonly DASHBOARD_UUID = process.env.DASHBOARD_UUID;
  private readonly SUPERSET_URL = process.env.SUPERSET_URL || 'http://localhost:8088';

  /**
   * Guest Token生成（URL Parameters対応）
   * @param departmentId 部署ID（URLパラメータとして渡される）
   * @param username ユーザー名
   */
  generateGuestToken(departmentId: number, username: string): string {
    const now = Math.floor(Date.now() / 1000);

    const payload = {
      user: {
        username: username,
        first_name: 'Guest',
        last_name: 'User',
      },
      resources: [
        {
          type: 'dashboard',
          id: this.DASHBOARD_UUID,
        },
      ],
      rls_rules: [
        // セキュリティ層としてRLSも併用（推奨）
        {
          clause: `department_id = ${departmentId}`,
        },
      ],
      iat: now,
      exp: now + 300, // 5分間有効
      aud: `${this.SUPERSET_URL}/`,
      type: 'guest',
    };

    return jwt.sign(payload, this.SUPERSET_SECRET_KEY, { algorithm: 'HS256' });
  }

  /**
   * 部署一覧取得（デモ用）
   */
  getDepartments() {
    return [
      { id: 101, name: '営業部', region: 'Tokyo' },
      { id: 102, name: '開発部', region: 'Osaka' },
      { id: 103, name: 'マーケティング部', region: 'Tokyo' },
    ];
  }
}
```

#### 2.4 コントローラー

**`src/superset/superset.controller.ts`**:

```typescript
import { Controller, Get, Query } from '@nestjs/common';
import { SupersetService } from './superset.service';

@Controller('api/superset')
export class SupersetController {
  constructor(private readonly supersetService: SupersetService) {}

  /**
   * Guest Token取得エンドポイント
   * GET /api/superset/guest-token?departmentId=101
   */
  @Get('guest-token')
  getGuestToken(@Query('departmentId') departmentId: string) {
    const deptId = parseInt(departmentId, 10);

    if (isNaN(deptId)) {
      return { error: 'Invalid department ID' };
    }

    const token = this.supersetService.generateGuestToken(
      deptId,
      `dept_${deptId}_user`,
    );

    return {
      token,
      departmentId: deptId,
    };
  }

  /**
   * 部署一覧取得エンドポイント
   * GET /api/superset/departments
   */
  @Get('departments')
  getDepartments() {
    return this.supersetService.getDepartments();
  }
}
```

#### 2.5 モジュール設定

**`src/superset/superset.module.ts`**:

```typescript
import { Module } from '@nestjs/common';
import { SupersetController } from './superset.controller';
import { SupersetService } from './superset.service';

@Module({
  controllers: [SupersetController],
  providers: [SupersetService],
})
export class SupersetModule {}
```

**`src/app.module.ts`**:

```typescript
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { SupersetModule } from './superset/superset.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
    }),
    SupersetModule,
  ],
})
export class AppModule {}
```

#### 2.6 CORS設定

**`src/main.ts`**:

```typescript
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // CORS有効化
  app.enableCors({
    origin: process.env.FRONTEND_URL || 'http://localhost:4200',
    credentials: true,
  });

  await app.listen(process.env.PORT || 3001);
  console.log(`Backend running on: http://localhost:${process.env.PORT || 3001}`);
}
bootstrap();
```

---

### 3. Frontend (Angular v20)

#### 3.1 プロジェクト作成

```bash
cd ../
ng new frontend --routing --style=css
cd frontend

# Superset Embedded SDK インストール
npm install @superset-ui/embedded-sdk
```

#### 3.2 Supersetサービス

**`src/app/services/superset.service.ts`**:

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Department {
  id: number;
  name: string;
  region: string;
}

export interface GuestTokenResponse {
  token: string;
  departmentId: number;
}

@Injectable({
  providedIn: 'root'
})
export class SupersetService {
  private readonly API_URL = 'http://localhost:3001/api/superset';

  constructor(private http: HttpClient) {}

  /**
   * 部署一覧取得
   */
  getDepartments(): Observable<Department[]> {
    return this.http.get<Department[]>(`${this.API_URL}/departments`);
  }

  /**
   * Guest Token取得
   * @param departmentId 部署ID
   */
  getGuestToken(departmentId: number): Observable<GuestTokenResponse> {
    return this.http.get<GuestTokenResponse>(
      `${this.API_URL}/guest-token?departmentId=${departmentId}`
    );
  }
}
```

#### 3.3 Dashboardコンポーネント

**`src/app/components/dashboard/dashboard.component.ts`**:

```typescript
import { Component, OnInit } from '@angular/core';
import { embedDashboard } from '@superset-ui/embedded-sdk';
import { SupersetService, Department } from '../../services/superset.service';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  departments: Department[] = [];
  selectedDepartmentId: number | null = null;
  isLoading = false;
  error: string | null = null;

  constructor(private supersetService: SupersetService) {}

  ngOnInit() {
    this.loadDepartments();
  }

  /**
   * 部署一覧を読み込む
   */
  loadDepartments() {
    this.supersetService.getDepartments().subscribe({
      next: (departments) => {
        this.departments = departments;
        // 最初の部署を自動選択
        if (departments.length > 0) {
          this.selectDepartment(departments[0].id);
        }
      },
      error: (err) => {
        this.error = '部署一覧の取得に失敗しました';
        console.error(err);
      }
    });
  }

  /**
   * 部署を選択してDashboardを表示
   * @param departmentId 部署ID
   */
  selectDepartment(departmentId: number) {
    this.selectedDepartmentId = departmentId;
    this.isLoading = true;
    this.error = null;

    // 既存のDashboardをクリア
    const container = document.getElementById('dashboard-container');
    if (container) {
      container.innerHTML = '';
    }

    // Dashboardを埋め込む
    this.embedDashboard(departmentId);
  }

  /**
   * Superset Dashboardを埋め込む
   * @param departmentId 部署ID
   */
  private embedDashboard(departmentId: number) {
    const dashboardId = 'YOUR_DASHBOARD_UUID'; // 環境変数から取得することを推奨

    embedDashboard({
      id: dashboardId,
      supersetDomain: 'http://localhost:8088',
      mountPoint: document.getElementById('dashboard-container')!,
      fetchGuestToken: () =>
        this.supersetService.getGuestToken(departmentId)
          .toPromise()
          .then(response => response!.token),
      dashboardUiConfig: {
        hideTitle: false,
        hideChartControls: false,
        hideTab: false,
        // ★重要: URLパラメータを渡す
        urlParams: {
          department_id: departmentId, // Jinjaテンプレートで {{ url_param('department_id') }} として取得可能
        },
      },
    })
    .then(() => {
      this.isLoading = false;
      console.log(`Dashboard loaded for department ${departmentId}`);
    })
    .catch((error) => {
      this.isLoading = false;
      this.error = 'Dashboardの読み込みに失敗しました';
      console.error('Dashboard embedding error:', error);
    });
  }
}
```

#### 3.4 HTMLテンプレート

**`src/app/components/dashboard/dashboard.component.html`**:

```html
<div class="container">
  <h1>部署別売上分析</h1>

  <!-- 部署選択タブ -->
  <div class="department-tabs">
    <button
      *ngFor="let dept of departments"
      [class.active]="selectedDepartmentId === dept.id"
      (click)="selectDepartment(dept.id)"
      class="tab-button"
    >
      {{ dept.name }} ({{ dept.region }})
    </button>
  </div>

  <!-- エラーメッセージ -->
  <div *ngIf="error" class="error-message">
    {{ error }}
  </div>

  <!-- ローディング表示 -->
  <div *ngIf="isLoading" class="loading">
    <p>読み込み中...</p>
  </div>

  <!-- Superset Dashboard埋め込みエリア -->
  <div id="dashboard-container" class="dashboard-container"></div>
</div>
```

#### 3.5 CSS

**`src/app/components/dashboard/dashboard.component.css`**:

```css
.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  color: #333;
  margin-bottom: 20px;
}

.department-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  border-bottom: 2px solid #e0e0e0;
}

.tab-button {
  padding: 10px 20px;
  border: none;
  background-color: #f5f5f5;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
  border-radius: 4px 4px 0 0;
}

.tab-button:hover {
  background-color: #e0e0e0;
}

.tab-button.active {
  background-color: #1890ff;
  color: white;
}

.error-message {
  padding: 15px;
  background-color: #ffebee;
  color: #c62828;
  border-radius: 4px;
  margin-bottom: 20px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

.dashboard-container {
  width: 100%;
  height: 800px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}
```

#### 3.6 App Module設定

**`src/app/app.module.ts`**:

```typescript
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';

import { AppComponent } from './app.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';

@NgModule({
  declarations: [
    AppComponent,
    DashboardComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
```

**`src/app/app.component.html`**:

```html
<app-dashboard></app-dashboard>
```

---

## 動作確認手順

### 1. 全サービス起動

```bash
# Terminal 1: Superset
cd superset
TAG=5.0.0 docker compose -f docker-compose-image-tag.yml up

# Terminal 2: Backend
cd backend
npm run start:dev

# Terminal 3: Frontend
cd frontend
ng serve
```

### 2. 確認

1. **http://localhost:4200** にアクセス
2. 部署タブ（営業部、開発部、マーケティング部）が表示される
3. タブをクリックすると、該当部署のデータのみが表示される

### 3. 動作確認ポイント

**営業部（ID: 101）を選択**:
- URLパラメータ: `department_id=101`
- 表示データ: 営業部の売上のみ（製品A, B, C）
- 合計金額: ¥185,000

**開発部（ID: 102）を選択**:
- URLパラメータ: `department_id=102`
- 表示データ: 開発部の売上のみ（製品X, Y, Z）
- 合計金額: ¥235,000

**マーケティング部（ID: 103）を選択**:
- URLパラメータ: `department_id=103`
- 表示データ: マーケティング部の売上のみ（製品P, Q, R）
- 合計金額: ¥75,000

### 4. SQLクエリ確認

Supersetのログで実際に実行されるSQLを確認:

```bash
docker logs superset_app | grep "SELECT"
```

期待されるSQL（営業部の場合）:
```sql
SELECT
    s.sale_date,
    s.department_id,
    d.name as department_name,
    d.region,
    s.product_name,
    s.amount,
    s.quantity
FROM sales s
JOIN departments d ON s.department_id = d.id
WHERE s.department_id = 101  -- ← url_param('department_id') から取得
ORDER BY s.sale_date DESC
```

---

## セキュリティ考慮事項

### 1. URL Parameter改ざん対策

**問題**: ユーザーがURLを直接編集して他部署のデータを見られる

**対策**:

#### 対策A: RLSとの併用（推奨）

Guest Token生成時にRLSも設定:

```typescript
rls_rules: [
  {
    clause: `department_id = ${departmentId}`,
  },
],
```

これにより、URL Parameterが改ざんされてもRLSで制限される。

#### 対策B: バックエンドでの検証

```typescript
@Get('guest-token')
getGuestToken(
  @Query('departmentId') departmentId: string,
  @Headers('authorization') authHeader: string
) {
  // 1. ユーザー認証
  const user = this.verifyUserToken(authHeader);

  // 2. 部署アクセス権限チェック
  if (!user.allowedDepartments.includes(parseInt(departmentId))) {
    throw new ForbiddenException('この部署へのアクセス権限がありません');
  }

  // 3. Guest Token生成
  const token = this.supersetService.generateGuestToken(
    parseInt(departmentId),
    user.username
  );

  return { token, departmentId };
}
```

### 2. Token有効期限

```typescript
exp: now + 300, // 5分間のみ有効
```

短い有効期限でセキュリティリスクを軽減。

### 3. HTTPS使用（本番環境）

```typescript
// 本番環境ではHTTPSを使用
const SUPERSET_URL = process.env.NODE_ENV === 'production'
  ? 'https://superset.example.com'
  : 'http://localhost:8088';
```

---

## トラブルシューティング

### 問題1: Dashboard が表示されない

**原因**: Guest Token の`aud`が間違っている

**解決策**:
```typescript
aud: `${this.SUPERSET_URL}/`, // 末尾のスラッシュが必要
```

### 問題2: URL Parameter がSQLに反映されない

**原因**: `dashboardUiConfig.urlParams` の設定ミス

**解決策**:
```typescript
urlParams: {
  department_id: departmentId, // キー名がSQL内の url_param('department_id') と一致している必要がある
},
```

### 問題3: RLS と URL Parameter で二重フィルタリングされない

**原因**: RLS は WHERE句の外側に適用される

**解決策**: これは正常な動作。RLSは最終的なセーフティネットとして機能。

### 問題4: CORS エラー

**原因**: Backend の CORS 設定が不足

**解決策**:
```typescript
app.enableCors({
  origin: 'http://localhost:4200',
  credentials: true,
});
```

---

## 参考資料

- [Superset Embedded SDK Documentation](https://github.com/apache/superset/tree/master/superset-embedded-sdk)
- [Superset SQL Templating](https://superset.apache.org/docs/configuration/sql-templating/)
- [Nest.js Documentation](https://docs.nestjs.com/)
- [Angular Documentation](https://angular.dev/)

---

## 次のステップ

1. **認証機能追加**: JWT認証でユーザーごとにアクセス制御
2. **複数Dashboard**: 部署ごとに異なるDashboardを表示
3. **リアルタイムデータ**: WebSocketでデータ更新通知
4. **監査ログ**: どのユーザーがどのデータを見たか記録

---

**作成日**: 2026-01-11
**想定環境**:
- Angular v20
- Nest.js v11
- Superset 5.0
- Node.js 18+
- Docker Desktop
