#!/usr/bin/env python3
"""
Dashboard 15 に Time column フィルターを追加
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

def get_dashboard_info():
    """Dashboard情報を取得"""
    print(f"📊 Dashboard {DASHBOARD_ID} の情報を取得中...")
    response = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{DASHBOARD_ID}")

    if response.status_code == 200:
        data = response.json()['result']
        json_metadata = data.get('json_metadata')
        if json_metadata:
            metadata = json.loads(json_metadata) if isinstance(json_metadata, str) else json_metadata
            print(f"現在のフィルター設定:")
            print(json.dumps(metadata.get('native_filter_configuration', []), indent=2, ensure_ascii=False))
        return data
    return None

def add_time_column_filter():
    """Time columnフィルターを追加"""
    print("\n🔧 Time columnフィルターを追加中...")

    # Dashboard情報取得
    response = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{DASHBOARD_ID}")
    if response.status_code != 200:
        print("❌ Dashboard情報取得失敗")
        return False

    dashboard = response.json()['result']
    position_json = dashboard.get('position_json')
    json_metadata = dashboard.get('json_metadata')

    if json_metadata:
        metadata = json.loads(json_metadata) if isinstance(json_metadata, str) else json_metadata
    else:
        metadata = {}

    # Native filter設定
    filter_config = {
        "NATIVE_FILTER-1": {
            "id": "NATIVE_FILTER-1",
            "name": "期間フィルター",
            "filterType": "filter_time",
            "targets": [
                {
                    "datasetId": 29,  # product_defect_analysis Dataset ID
                    "column": {
                        "name": "test_date"
                    }
                }
            ],
            "defaultDataMask": {
                "extraFormData": {},
                "filterState": {},
                "ownState": {}
            },
            "controlValues": {
                "enableEmptyFilter": False,
                "defaultToFirstItem": False,
                "multiSelect": True,
                "searchAllOptions": False,
                "inverseSelection": False
            },
            "scope": {
                "rootPath": ["ROOT_ID"],
                "excluded": []
            },
            "cascadeParentIds": [],
            "type": "NATIVE_FILTER",
            "description": "",
            "chartsInScope": [130, 131],  # 円グラフとテーブル
            "tabsInScope": []
        }
    }

    metadata["native_filter_configuration"] = [filter_config["NATIVE_FILTER-1"]]
    metadata["cross_filters_enabled"] = True

    update_data = {
        "json_metadata": json.dumps(metadata),
    }

    response = session.put(f"{SUPERSET_URL}/api/v1/dashboard/{DASHBOARD_ID}", json=update_data)

    if response.status_code == 200:
        print("✅ フィルター追加成功")
        return True
    else:
        print(f"❌ フィルター追加失敗: {response.status_code}")
        print(f"Response: {response.text}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Dashboard Time Filter 追加")
    print("=" * 60)
    print()

    if login():
        get_dashboard_info()
        if add_time_column_filter():
            print()
            print("=" * 60)
            print("✅ 完了")
            print("=" * 60)
            print()
            print(f"📊 Dashboard URL:")
            print(f"   {SUPERSET_URL}/superset/dashboard/{DASHBOARD_ID}/")
            print()
            print("Dashboardをリロードしてフィルターを確認してください")
