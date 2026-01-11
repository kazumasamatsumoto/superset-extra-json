# 🎉 重要な発見: RLS は GROUP BY の前に適用される！

## 検証結果

PostgreSQL のクエリログから、RLS (Row Level Security) が実際にどのように SQL に組み込まれるかを確認しました。

### 実際に実行されたSQL

```sql
SELECT DATE_TRUNC('day', sale_date) AS sale_date,
       sum(amount) AS "SUM(amount)"
FROM (
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
) AS virtual_table
WHERE (department_id = 103)        -- ★★★ RLSがここに適用される ★★★
GROUP BY DATE_TRUNC('day', sale_date)
ORDER BY "SUM(amount)" DESC
```

## 結論

### ❌ 誤解していたこと
> RLSはWHERE句を大外（GROUP BY後）に適用するため、集計前のフィルタリングができない

### ✅ 実際の動作
**RLS の WHERE 句は、サブクエリ直後、GROUP BY の前に適用される！**

つまり：
1. Virtual Dataset の SELECT がサブクエリとして実行される
2. RLS の `clause` が WHERE として追加される ← **ここが重要**
3. その後に GROUP BY / ORDER BY が適用される

## 影響

### 元の要求
> GROUP BYの前段階で department_id でフィルタリングしたい

### 解決策
**RLS で実現可能！** 追加の実装は不要です。

## 実装方法

### Guest Token 生成（Backend）

```typescript
// superset.service.ts
generateGuestToken(departmentId: number, username: string): string {
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
        id: this.EMBEDDED_DASHBOARD_UUID,
      },
    ],
    rls_rules: [
      {
        clause: `department_id = ${departmentId}`  // ★ これでGROUP BY前にフィルタリング可能
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

### Dataset Extra JSON は不要

Dataset の `extra` フィールドに Jinja テンプレートを追加する必要はありません。

```sql
-- これは削除してOK
UPDATE tables
SET extra = '{}'  -- または NULL
WHERE table_name = 'sales_by_department';
```

### Frontend - 変更なし

既存の Angular コードで動作します。部署を切り替えると、新しい Guest Token が発行され、自動的にフィルタリングされます。

## スケーラビリティ

### マルチテナント対応

顧客ごと、ユーザーごと、テナントごとにフィルタリングする場合も同様に動作します：

```typescript
// 例: 顧客ID でフィルタリング
rls_rules: [
  {
    clause: `customer_id = '${customerId}'`
  }
]
```

```typescript
// 例: 複数条件
rls_rules: [
  {
    clause: `customer_id = '${customerId}' AND region = '${region}'`
  }
]
```

### Dashboard/Chart の管理

- ✅ 単一の Dashboard で全ユーザー対応可能
- ✅ 単一の Dataset で全データソース対応可能
- ✅ Chart も共通で利用可能

**数百〜数千のユーザーがいても、Dashboard/Chart は1つだけでOK！**

## 注意点

### SQLインジェクション対策

Guest Token 生成時に、パラメータをサニタイズする必要があります：

```typescript
generateGuestToken(departmentId: number, username: string): string {
  // 入力値検証
  if (!Number.isInteger(departmentId) || departmentId <= 0) {
    throw new Error('Invalid department ID');
  }

  const payload = {
    // ...
    rls_rules: [
      {
        clause: `department_id = ${departmentId}`  // 数値なので安全
      }
    ],
  };

  return jwt.sign(payload, this.SUPERSET_SECRET_KEY, { algorithm: 'HS256' });
}
```

文字列の場合：

```typescript
// 文字列の場合はエスケープが必要
const escapedCustomerId = customerId.replace(/'/g, "''");  // SQL escape
rls_rules: [
  {
    clause: `customer_id = '${escapedCustomerId}'`
  }
]
```

またはParameterized Queryのアプローチ：

```typescript
// Superset 5.0+ では以下の書き方も可能（要確認）
rls_rules: [
  {
    clause: "customer_id = :customer_id",
    parameters: { customer_id: customerId }
  }
]
```

## まとめ

### 元々の問題

- ❌ `extra_json` + Jinja Template は Superset 5.0 で未実装
- ❌ Guest Token の `extra_json` にアクセスする方法がない

### 実際の解決策

- ✅ **RLS (Row Level Security) で実現可能**
- ✅ GROUP BY の前にフィルタリングが適用される
- ✅ マルチテナント対応も可能
- ✅ Dashboard/Chart を複数作る必要なし

### 次のステップ

1. Dataset Extra JSON の Jinja Template を削除
2. Guest Token に RLS を設定
3. 動作確認

---

**検証日**: 2026-01-11
**対象バージョン**: Superset 5.0.0
**検証方法**: PostgreSQL クエリログ分析
