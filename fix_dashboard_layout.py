#!/usr/bin/env python3
"""
既存のダッシュボードレイアウトを修正するスクリプト
"""

import requests
import json

SUPERSET_URL = "http://localhost:8088"
USERNAME = "admin"
PASSWORD = "admin"
DASHBOARD_ID = 14

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

def get_dashboard_info():
    """Dashboard情報を取得"""
    print(f"📊 Dashboard ID {DASHBOARD_ID} の情報を取得中...")
    response = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{DASHBOARD_ID}")

    if response.status_code == 200:
        data = response.json()['result']
        print(f"✅ Dashboard: {data['dashboard_title']}")

        # Chart IDsを取得
        slices = data.get('slices', [])
        chart_ids = [s['id'] for s in slices]
        print(f"📈 Charts: {chart_ids}")

        return chart_ids
    else:
        print(f"❌ Dashboard情報取得失敗: {response.status_code}")
        return []

def fix_dashboard_layout(chart_ids):
    """Dashboardレイアウトを修正"""
    print("🔧 Dashboardレイアウトを修正中...")

    if len(chart_ids) < 3:
        print("❌ Chart数が不足しています")
        return False

    pie_chart_id = chart_ids[0]
    table_chart_id = chart_ids[1]
    bar_chart_id = chart_ids[2]

    # 正しいposition_json構造
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

    update_data = {
        "position_json": json.dumps(position_json),
        "json_metadata": json.dumps({"cross_filters_enabled": True}),
    }

    response = session.put(f"{SUPERSET_URL}/api/v1/dashboard/{DASHBOARD_ID}", json=update_data)

    if response.status_code == 200:
        print("✅ Dashboardレイアウト修正成功")
        return True
    else:
        print(f"❌ Dashboardレイアウト修正失敗: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def main():
    print("=" * 60)
    print("Dashboard レイアウト修正スクリプト")
    print("=" * 60)
    print()

    if not login():
        return

    chart_ids = get_dashboard_info()
    if not chart_ids:
        return

    if fix_dashboard_layout(chart_ids):
        print()
        print("=" * 60)
        print("✅ 修正完了！")
        print("=" * 60)
        print()
        print(f"📊 Dashboard URL:")
        print(f"   {SUPERSET_URL}/superset/dashboard/{DASHBOARD_ID}/")
        print()

if __name__ == "__main__":
    main()
