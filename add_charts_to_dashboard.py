#!/usr/bin/env python3
"""
既存のDashboardにChartを追加するスクリプト
"""

import requests
import json

SUPERSET_URL = "http://localhost:8088"
USERNAME = "admin"
PASSWORD = "admin"
DASHBOARD_ID = 15

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

def get_recent_charts():
    """最近作成されたChartを取得"""
    print("📊 Chart一覧を取得中...")
    response = session.get(
        f"{SUPERSET_URL}/api/v1/chart/",
        params={"q": json.dumps({"page_size": 10, "order_column": "id", "order_direction": "desc"})}
    )

    if response.status_code == 200:
        charts = response.json()['result'][:3]  # 最新3件
        print(f"✅ {len(charts)}件のChartが見つかりました:")
        for chart in charts:
            print(f"  - ID: {chart['id']}, Name: {chart['slice_name']}")
        return [c['id'] for c in charts]
    return []

def get_dashboard_current_layout():
    """現在のDashboard情報を取得"""
    print(f"📊 Dashboard ID {DASHBOARD_ID} の情報を取得中...")
    response = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{DASHBOARD_ID}")

    if response.status_code == 200:
        data = response.json()['result']
        print(f"✅ Dashboard: {data['dashboard_title']}")

        position_json = data.get('position_json')
        if position_json:
            return json.loads(position_json) if isinstance(position_json, str) else position_json
        else:
            return None
    return None

def update_dashboard_layout(chart_ids):
    """DashboardレイアウトにChartを追加"""
    print("🔧 Dashboardレイアウトを更新中...")

    if len(chart_ids) < 3:
        print("❌ Chart数が不足しています")
        return False

    # chart_idsは降順なので、逆順にする
    chart_ids = list(reversed(chart_ids))

    pie_chart_id = chart_ids[0]
    table_chart_id = chart_ids[1]
    bar_chart_id = chart_ids[2]

    print(f"  Pie Chart: {pie_chart_id}")
    print(f"  Table Chart: {table_chart_id}")
    print(f"  Bar Chart: {bar_chart_id}")

    # 完全な position_json 構造
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

    # json_metadata にも cross_filters_enabled を設定
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
        print("✅ Dashboardレイアウト更新成功")
        return True
    else:
        print(f"❌ Dashboardレイアウト更新失敗: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def main():
    print("=" * 60)
    print("Dashboard に Chart を追加")
    print("=" * 60)
    print()

    if not login():
        return

    chart_ids = get_recent_charts()
    if not chart_ids:
        return

    if update_dashboard_layout(chart_ids):
        print()
        print("=" * 60)
        print("✅ 完了！")
        print("=" * 60)
        print()
        print(f"📊 Dashboard URL:")
        print(f"   {SUPERSET_URL}/superset/dashboard/{DASHBOARD_ID}/")
        print()

if __name__ == "__main__":
    main()
