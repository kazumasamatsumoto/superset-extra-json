#!/usr/bin/env python3
"""
Bar Chart (通常の棒グラフ) を作成してDashboardに追加
"""

import requests
import json
import time

SUPERSET_URL = "http://localhost:8088"
USERNAME = "admin"
PASSWORD = "admin"
DASHBOARD_ID = 15
DATASET_ID = 29  # product_defect_analysis_v1768111609

session = requests.Session()

def login():
    """Supersetにログイン"""
    login_data = {"username": USERNAME, "password": PASSWORD, "provider": "db"}
    response = session.post(f"{SUPERSET_URL}/api/v1/security/login", json=login_data)

    if response.status_code == 200:
        access_token = response.json()['access_token']
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
    return False

def delete_old_bar_chart():
    """古い棒グラフ (ID: 132) を削除"""
    print("🗑️  古い棒グラフ (ID: 132) を削除中...")
    response = session.delete(f"{SUPERSET_URL}/api/v1/chart/132")

    if response.status_code == 200:
        print("✅ 削除成功")
    else:
        print(f"⚠️  削除失敗またはすでに削除済み: {response.status_code}")

def create_bar_chart():
    """Bar Chart (通常の棒グラフ) を作成"""
    print("📊 Bar Chartを作成中...")

    chart_data = {
        "slice_name": "製品別ステータス内訳",
        "viz_type": "bar",
        "datasource_id": DATASET_ID,
        "datasource_type": "table",
        "params": json.dumps({
            "datasource": f"{DATASET_ID}__table",
            "viz_type": "bar",
            "metrics": ["count"],
            "groupby": ["product_name"],
            "columns": ["status"],
            "row_limit": 10000,
            "show_legend": True,
            "y_axis_format": ",d",
            "x_axis_label": "製品名",
            "y_axis_label": "件数",
        }),
    }

    response = session.post(f"{SUPERSET_URL}/api/v1/chart/", json=chart_data)

    if response.status_code == 201:
        chart_id = response.json()['id']
        print(f"✅ Bar Chart作成成功 (ID: {chart_id})")
        return chart_id
    else:
        print(f"❌ Bar Chart作成失敗: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def update_dashboard_layout(new_bar_chart_id):
    """Dashboardレイアウトを更新"""
    print(f"🔧 Dashboardレイアウトを更新中 (新しい棒グラフID: {new_bar_chart_id})...")

    PIE_CHART_ID = 130
    TABLE_CHART_ID = 131

    position_json = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {
            "type": "ROOT",
            "id": "ROOT_ID",
            "children": ["GRID_ID"]
        },
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
                "chartId": PIE_CHART_ID
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
                "chartId": new_bar_chart_id
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
                "chartId": TABLE_CHART_ID
            }
        },
    }

    json_metadata = {
        "cross_filters_enabled": True,
        "native_filter_configuration": []
    }

    update_data = {
        "position_json": json.dumps(position_json),
        "json_metadata": json.dumps(json_metadata),
    }

    response = session.put(f"{SUPERSET_URL}/api/v1/dashboard/{DASHBOARD_ID}", json=update_data)

    if response.status_code == 200:
        print("✅ Dashboard更新成功")
        return True
    else:
        print(f"❌ Dashboard更新失敗: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def main():
    print("=" * 60)
    print("Bar Chart 再作成")
    print("=" * 60)
    print()

    if not login():
        return

    delete_old_bar_chart()
    time.sleep(1)

    new_chart_id = create_bar_chart()
    if not new_chart_id:
        return

    time.sleep(1)

    if update_dashboard_layout(new_chart_id):
        print()
        print("=" * 60)
        print("✅ 完了")
        print("=" * 60)
        print()
        print(f"📊 Dashboard URL:")
        print(f"   {SUPERSET_URL}/superset/dashboard/{DASHBOARD_ID}/")
        print()
        print("次のステップ:")
        print("  1. Dashboardにアクセスして3つのChartが表示されることを確認")
        print("  2. 期間フィルターを追加 (test_date カラム)")
        print("  3. 2024年1月/2月で切り替えてステータス変化を確認")
        print()

if __name__ == "__main__":
    main()
