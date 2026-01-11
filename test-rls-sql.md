# RLS (Row Level Security) の実際のSQL実行順序を検証

## 検証目的

RLSのWHERE句が本当に「GROUP BYの後（外側）」に適用されるのか、それとも実は「サブクエリの内側」に適用されるのかを確認する。

## 仮説

### 仮説A: RLSはGROUP BY後に適用される（ユーザーの認識）
```sql
SELECT department_id, SUM(amount) as total
FROM (
    SELECT * FROM sales
    GROUP BY department_id
) subquery
WHERE department_id = 101  -- ★ RLSがここに適用
```
→ これだと集計後のフィルタリングになり無意味

### 仮説B: RLSは実際にはサブクエリ内に適用される
```sql
SELECT department_id, SUM(amount) as total
FROM (
    SELECT * FROM sales
    WHERE department_id = 101  -- ★ RLSがここに適用
) subquery
GROUP BY department_id
```
→ これならGROUP BY前のフィルタリングになる

## 検証方法

1. Superset側でSQL Labのクエリログを有効化
2. RLSを設定したGuest Tokenでダッシュボードにアクセス
3. 実際に実行されたSQLを確認
4. WHERE句の位置を確認

## 次のステップ

Supersetのログレベルを上げて、実際に実行されるSQLを確認する。
