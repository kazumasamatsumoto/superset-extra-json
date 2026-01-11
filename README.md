# Superset 5.0 動的フィルタリング検証プロジェクト

Apache Superset 5.0 の Embedded SDK を使用した動的フィルタリング機能の検証プロジェクトです。

## 📋 プロジェクト概要

**検証目的**: Guest Token の RLS (Row Level Security) を使用して、GROUP BY の前段階でデータをフィルタリングできるかを検証

**結論**: ✅ **RLS で実現可能** - GROUP BY の前にフィルタリングが適用されることを確認

## 🏗️ アーキテクチャ

- **Backend**: Nest.js 10.x + TypeScript
- **Frontend**: Angular 21.x
- **BI Tool**: Apache Superset 5.0.0
- **Embedded SDK**: @superset-ui/embedded-sdk 0.3.0
- **Database**: PostgreSQL

## 📁 プロジェクト構成

```
research-superset/
├── superset-demo-backend/       # Nest.js API (Guest Token 生成)
├── superset-demo-frontend/      # Angular アプリ (Dashboard 埋め込み)
├── VERIFICATION_RESULTS.md      # extra_json アプローチの検証結果
├── RLS_ACTUALLY_WORKS.md        # RLS が正しく動作することの検証
├── RLS_LIMITATION.md            # RLS の制約と設計原則
├── PRACTICAL_SOLUTION.md        # 実用的な解決策（複数Dashboard案）
└── test-*.png                   # 動作確認スクリーンショット
```

## 🎯 検証結果サマリー

### ❌ 実現不可能な方法: extra_json + Jinja Template

Superset 5.0 では Guest Token の `extra_json` フィールドを Jinja テンプレートから参照する機能が未実装。

- `current_user().extra_json` → Guest ユーザーでは動作しない
- `get_guest_user_attribute()` → 提案段階（SIP-174）
- `guest_token_template_variable()` → 提案段階

### ✅ 実現可能な方法: RLS (Row Level Security)

Guest Token の `rls_rules` を使用することで、GROUP BY の前段階でのフィルタリングが可能。

**生成される SQL**:
```sql
SELECT DATE_TRUNC('day', sale_date), SUM(amount)
FROM (
    SELECT * FROM sales  -- Dataset の SQL
) AS virtual_table
WHERE (department_id = 101)  -- ★ RLS が GROUP BY の前に適用
GROUP BY DATE_TRUNC('day', sale_date)
```

## 🚀 セットアップ

### 1. Backend (Nest.js)

```bash
cd superset-demo-backend
npm install
npm run build
npm start
```

API: http://localhost:3001

### 2. Frontend (Angular)

```bash
cd superset-demo-frontend
npm install
npm start
```

Web UI: http://localhost:4200

### 3. Superset (Docker Compose)

```bash
cd ../superset-docker
TAG=5.0.0 docker compose up -d
```

Superset: http://localhost:8088

## 🔧 実装のポイント

### Guest Token 生成 (Backend)

```typescript
// superset.service.ts
generateGuestToken(departmentId: number, username: string): string {
  const payload = {
    user: {
      username,
      first_name: 'Guest',
      last_name: 'User',
    },
    resources: [
      {
        type: 'dashboard',
        id: this.EMBEDDED_DASHBOARD_UUID,
      },
    ],
    rls_rules: [
      {
        clause: `department_id = ${departmentId}`  // 動的フィルタリング
      }
    ],
    iat: now,
    exp: now + 86400,
    aud: 'http://superset:8088/',
    type: 'guest',
  };

  return jwt.sign(payload, this.SUPERSET_SECRET_KEY, { algorithm: 'HS256' });
}
```

### Dashboard 埋め込み (Frontend)

```typescript
// dashboard.component.ts
import { embedDashboard } from '@superset-ui/embedded-sdk';

this.currentEmbed = await embedDashboard({
  id: '7aaabc03-2c47-4540-8233-f22bbdb2cc81',
  supersetDomain: 'http://localhost:8088',
  mountPoint: container!,
  fetchGuestToken: async () => response.token,
  dashboardUiConfig: {
    hideTitle: false,
    hideChartControls: false,
    hideTab: false,
  },
});
```

## 📊 動作確認

プロジェクトには以下のスクリーンショットが含まれています：

- `test-rls-営業部.png` - 営業部のダッシュボード（department_id = 101）
- `test-rls-開発部.png` - 開発部のダッシュボード（department_id = 102）
- `test-rls-マーケティング部.png` - マーケティング部のダッシュボード（department_id = 103）

各部署で異なるデータが表示されることを確認済み。

## ⚠️ RLS の設計原則

動的フィルタリング（RLS）を使う場合の重要な設計原則：

1. **Dataset には必ずフィルタリング対象のカラムを保持する**
   ```sql
   -- ✅ Good: department_id を保持
   SELECT id, sale_date, amount, department_id FROM sales

   -- ❌ Bad: department_id を失う
   SELECT sale_date, SUM(amount) FROM sales GROUP BY sale_date
   ```

2. **GROUP BY を使う場合も、フィルタリング対象カラムを含める**
   ```sql
   -- ✅ Good
   SELECT department_id, DATE_TRUNC('day', sale_date), SUM(amount)
   FROM sales
   GROUP BY department_id, DATE_TRUNC('day', sale_date)

   -- ❌ Bad: department_id が GROUP BY に含まれていない
   SELECT DATE_TRUNC('day', sale_date), SUM(amount)
   FROM sales
   GROUP BY DATE_TRUNC('day', sale_date)
   ```

3. **集約は極力 Chart 側で行う（Dataset 側では最小限に）**

詳細は `RLS_LIMITATION.md` を参照。

## 📚 ドキュメント

- [VERIFICATION_RESULTS.md](./VERIFICATION_RESULTS.md) - extra_json アプローチの検証結果
- [RLS_ACTUALLY_WORKS.md](./RLS_ACTUALLY_WORKS.md) - RLS の動作確認
- [RLS_LIMITATION.md](./RLS_LIMITATION.md) - RLS の制約と設計原則
- [PRACTICAL_SOLUTION.md](./PRACTICAL_SOLUTION.md) - 複数 Dashboard アプローチ
- [EMBEDDED_SDK_IMPLEMENTATION.md](./EMBEDDED_SDK_IMPLEMENTATION.md) - 実装ガイド

## 🔗 参考リンク

- [Apache Superset Documentation](https://superset.apache.org/docs/intro)
- [Superset Embedded SDK](https://github.com/apache/superset/tree/master/superset-embedded-sdk)
- [SIP-174: Guest User Attributes](https://github.com/apache/superset/issues/33922)
- [Discussion: Guest Token Template Variables](https://github.com/apache/superset/discussions/33918)

## 📝 検証日

2026-01-11

## 👤 検証者

Claude Code (Anthropic)

---

**ライセンス**: MIT
