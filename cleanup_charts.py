#!/usr/bin/env python3
"""
既存のチャートとデータセットをクリーンアップするスクリプト
"""

import requests
import json

SUPERSET_URL = "http://localhost:8088"
USERNAME = "admin"
PASSWORD = "admin"

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

def delete_charts():
    """全Chartを削除"""
    print("🗑️  Chartを削除中...")
    response = session.get(f"{SUPERSET_URL}/api/v1/chart/")

    if response.status_code == 200:
        charts = response.json()['result']
        print(f"📊 {len(charts)}件のChartが見つかりました")

        for chart in charts:
            chart_id = chart['id']
            chart_name = chart['slice_name']
            print(f"  削除中: {chart_name} (ID: {chart_id})")

            delete_response = session.delete(f"{SUPERSET_URL}/api/v1/chart/{chart_id}")
            if delete_response.status_code == 200:
                print(f"    ✅ 削除成功")
            else:
                print(f"    ❌ 削除失敗: {delete_response.status_code}")

def delete_datasets():
    """全Datasetを削除"""
    print("🗑️  Datasetを削除中...")
    response = session.get(f"{SUPERSET_URL}/api/v1/dataset/")

    if response.status_code == 200:
        datasets = response.json()['result']
        print(f"📊 {len(datasets)}件のDatasetが見つかりました")

        for dataset in datasets:
            dataset_id = dataset['id']
            dataset_name = dataset['table_name']
            print(f"  削除中: {dataset_name} (ID: {dataset_id})")

            delete_response = session.delete(f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}")
            if delete_response.status_code == 200:
                print(f"    ✅ 削除成功")
            else:
                print(f"    ❌ 削除失敗: {delete_response.status_code} - {delete_response.text}")
    else:
        print("  ℹ️  Datasetが見つかりません")

if __name__ == "__main__":
    print("=" * 60)
    print("Cleanup スクリプト")
    print("=" * 60)
    print()

    if login():
        delete_charts()
        delete_datasets()
        print()
        print("✅ クリーンアップ完了")
