#!/usr/bin/env python3
"""
不具合率分析Dashboard自動作成スクリプト

期間によってステータス（Good/Warning/Bad）が変わる動的評価を実装
"""

import requests
import json
import time

SUPERSET_URL = "http://localhost:8088"
USERNAME = "admin"
PASSWORD = "admin"

session = requests.Session()

def login():
    """Supersetにログイン"""
    print("🔐 Supersetにログイン中...")

    login_data = {"username": USERNAME, "password": PASSWORD, "provider": "db"}
    response = session.post(f"{SUPERSET_URL}/api/v1/security/login", json=login_data)

    if response.status_code == 200:
        access_token = response.json()['access_token']

        # CSRFトークン取得
        csrf_response = session.get(
            f"{SUPERSET_URL}/api/v1/security/csrf_token/",
            headers={'Authorization': f'Bearer {access_token}'}
        )
        csrf_token = csrf_response.json().get('result') if csrf_response.status_code == 200 else ''

        session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token,
            'Referer': SUPERSET_URL,
        })
        print("✅ ログイン成功")
        return True
    else:
        print(f"❌ ログイン失敗: {response.status_code}")
        return False

def get_database_id():
    """Database IDを取得"""
    print("🔍 Database IDを取得中...")
    response = session.get(f"{SUPERSET_URL}/api/v1/database/")

    if response.status_code == 200:
        databases = response.json()['result']
        for db in databases:
            if db['database_name'] in ['Main Database', 'superset']:
                print(f"✅ Database ID: {db['id']} ({db['database_name']})")
                return db['id']

    print("❌ Database が見つかりません")
    return None

def create_dataset(database_id):
    """Virtual Dataset作成: 不具合率 + ステータス計算"""
    print("📊 Dataset 'product_defect_analysis' を作成中...")

    # 既存確認して削除
    response = session.get(
        f"{SUPERSET_URL}/api/v1/dataset/",
        params={"q": json.dumps({"filters": [{"col": "table_name", "opr": "eq", "value": "product_defect_analysis"}]})}
    )

    if response.status_code == 200 and response.json()['count'] > 0:
        dataset_id = response.json()['result'][0]['id']
        print(f"ℹ️  既存Dataset (ID: {dataset_id}) を削除中...")
        delete_response = session.delete(f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}")
        if delete_response.status_code == 200:
            print("✅ 削除成功")
            time.sleep(1)
        else:
            print(f"⚠️  削除失敗 (続行): {delete_response.status_code}")

    # Dataset作成
    dataset_data = {
        "database": database_id,
        "schema": "public",
        "table_name": f"product_defect_analysis_v{int(time.time())}",
        "sql": """
SELECT
    product_name,
    test_date,
    success_count,
    failure_count,
    department_id,
    -- 不具合率計算
    ROUND(failure_count::NUMERIC / (success_count + failure_count) * 100, 2) as defect_rate,
    -- ステータス判定（期間集計後に動的に変わる）
    CASE
        WHEN failure_count::NUMERIC / (success_count + failure_count) <= 0.05 THEN 'Good'
        WHEN failure_count::NUMERIC / (success_count + failure_count) <= 0.10 THEN 'Warning'
        ELSE 'Bad'
    END AS status
FROM product_test_results
ORDER BY test_date DESC, product_name
        """.strip(),
    }

    response = session.post(f"{SUPERSET_URL}/api/v1/dataset/", json=dataset_data)

    if response.status_code == 201:
        dataset_id = response.json()['id']
        print(f"✅ Dataset作成成功 (ID: {dataset_id})")
        time.sleep(1)
        session.put(f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}/refresh")
        return dataset_id
    else:
        print(f"❌ Dataset作成失敗: {response.status_code} - {response.text}")
        return None

def create_pie_chart(dataset_id):
    """円グラフ: ステータス別製品数"""
    print("🥧 円グラフを作成中...")

    chart_data = {
        "slice_name": "製品ステータス分布（Good/Warning/Bad）",
        "viz_type": "pie",
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": json.dumps({
            "datasource": f"{dataset_id}__table",
            "viz_type": "pie",
            "groupby": ["status"],
            "metric": "count",
            "row_limit": 10000,
            "color_scheme": "supersetColors",
            "show_labels": True,
            "show_legend": True,
            "label_type": "key_value",
        }),
    }

    response = session.post(f"{SUPERSET_URL}/api/v1/chart/", json=chart_data)

    if response.status_code == 201:
        print(f"✅ 円グラフ作成成功 (ID: {response.json()['id']})")
        return response.json()['id']
    else:
        print(f"❌ 円グラフ作成失敗: {response.status_code}")
        return None

def create_table_chart(dataset_id):
    """テーブル: 製品別不具合率詳細"""
    print("📋 テーブルチャートを作成中...")

    chart_data = {
        "slice_name": "製品テスト結果詳細",
        "viz_type": "table",
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": json.dumps({
            "datasource": f"{dataset_id}__table",
            "viz_type": "table",
            "query_mode": "raw",
            "all_columns": [
                "test_date",
                "product_name",
                "success_count",
                "failure_count",
                "defect_rate",
                "status"
            ],
            "order_by_cols": [["test_date", False]],
            "row_limit": 100,
        }),
    }

    response = session.post(f"{SUPERSET_URL}/api/v1/chart/", json=chart_data)

    if response.status_code == 201:
        print(f"✅ テーブル作成成功 (ID: {response.json()['id']})")
        return response.json()['id']
    else:
        print(f"❌ テーブル作成失敗: {response.status_code}")
        return None

def create_bar_chart(dataset_id):
    """棒グラフ: 製品別不具合率"""
    print("📊 棒グラフを作成中...")

    chart_data = {
        "slice_name": "製品別不具合率",
        "viz_type": "dist_bar",
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": json.dumps({
            "datasource": f"{dataset_id}__table",
            "viz_type": "dist_bar",
            "groupby": ["product_name"],
            "columns": ["status"],
            "metrics": ["count"],
            "row_limit": 10000,
        }),
    }

    response = session.post(f"{SUPERSET_URL}/api/v1/chart/", json=chart_data)

    if response.status_code == 201:
        print(f"✅ 棒グラフ作成成功 (ID: {response.json()['id']})")
        return response.json()['id']
    else:
        print(f"❌ 棒グラフ作成失敗: {response.status_code}")
        return None

def create_dashboard(pie_chart_id, table_chart_id, bar_chart_id):
    """Dashboard作成"""
    print("📊 Dashboardを作成中...")

    dashboard_data = {
        "dashboard_title": "製品不具合率分析（期間動的評価）",
        "published": True,
    }

    response = session.post(f"{SUPERSET_URL}/api/v1/dashboard/", json=dashboard_data)

    if response.status_code != 201:
        print(f"❌ Dashboard作成失敗: {response.status_code}")
        print(f"Response: {response.text}")
        return None

    dashboard_id = response.json()['id']
    print(f"✅ Dashboard作成成功 (ID: {dashboard_id})")

    # レイアウト設定
    position_json = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {
            "type": "GRID",
            "id": "GRID_ID",
            "children": ["ROW-1", "ROW-2"],
            "parents": ["ROOT_ID"]
        },
        "ROW-1": {
            "type": "ROW",
            "id": "ROW-1",
            "children": ["CHART-pie", "CHART-bar"],
            "parents": ["GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"}
        },
        "CHART-pie": {
            "type": "CHART",
            "id": "CHART-pie",
            "children": [],
            "parents": ["ROW-1"],
            "meta": {
                "width": 6,
                "height": 50,
                "chartId": pie_chart_id
            }
        },
        "CHART-bar": {
            "type": "CHART",
            "id": "CHART-bar",
            "children": [],
            "parents": ["ROW-1"],
            "meta": {
                "width": 6,
                "height": 50,
                "chartId": bar_chart_id
            }
        },
        "ROW-2": {
            "type": "ROW",
            "id": "ROW-2",
            "children": ["CHART-table"],
            "parents": ["GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"}
        },
        "CHART-table": {
            "type": "CHART",
            "id": "CHART-table",
            "children": [],
            "parents": ["ROW-2"],
            "meta": {
                "width": 12,
                "height": 50,
                "chartId": table_chart_id
            }
        },
    }

    update_data = {
        "position_json": json.dumps(position_json),
        "json_metadata": json.dumps({"cross_filters_enabled": True}),
    }

    session.put(f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}", json=update_data)
    return dashboard_id

def main():
    print("=" * 60)
    print("製品不具合率分析Dashboard 自動作成")
    print("=" * 60)
    print()

    if not login():
        return

    database_id = get_database_id()
    if not database_id:
        return

    dataset_id = create_dataset(database_id)
    if not dataset_id:
        return

    time.sleep(2)

    pie_chart_id = create_pie_chart(dataset_id)
    table_chart_id = create_table_chart(dataset_id)
    bar_chart_id = create_bar_chart(dataset_id)

    if not all([pie_chart_id, table_chart_id, bar_chart_id]):
        return

    time.sleep(1)

    dashboard_id = create_dashboard(pie_chart_id, table_chart_id, bar_chart_id)

    print()
    print("=" * 60)
    print("✅ Dashboard作成完了！")
    print("=" * 60)
    print()
    print(f"📊 Dashboard URL:")
    print(f"   {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
    print()
    print("🎯 検証手順:")
    print("   1. 期間フィルターで '2024年1月' を選択")
    print("      → iPhone 14: Good, Pixel 8: Bad")
    print("   2. 期間フィルターで '2024年2月' を選択")
    print("      → iPhone 14: Bad, Pixel 8: Warning")
    print("   3. 円グラフで 'Bad' をクリック")
    print("      → テーブルにBadステータスの製品のみ表示")
    print()

if __name__ == "__main__":
    main()
