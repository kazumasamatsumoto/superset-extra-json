#!/usr/bin/env python3
"""
Dashboard 15 のレイアウトを更新するスクリプト
"""

import requests
import json

SUPERSET_URL = "http://localhost:8088"
USERNAME = "admin"
PASSWORD = "admin"
DASHBOARD_ID = 15

# Chart IDs (データベースから確認済み)
PIE_CHART_ID = 130
TABLE_CHART_ID = 131
BAR_CHART_ID = 132

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

def update_dashboard():
    """Dashboardレイアウトを更新"""
    print(f"🔧 Dashboard {DASHBOARD_ID} のレイアウトを更新中...")

    # position_json 構造
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
                "chartId": BAR_CHART_ID
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

if __name__ == "__main__":
    print("=" * 60)
    print("Dashboard レイアウト更新")
    print("=" * 60)
    print()

    if login():
        if update_dashboard():
            print()
            print("=" * 60)
            print("✅ 完了")
            print("=" * 60)
            print()
            print(f"📊 Dashboard URL:")
            print(f"   {SUPERSET_URL}/superset/dashboard/{DASHBOARD_ID}/")
            print()
