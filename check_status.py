#!/usr/bin/env python3
"""
Superset の Chart/Dataset 状態を確認するスクリプト
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
        session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        })
        return True
    return False

def check_datasets():
    """Dataset一覧を確認"""
    response = session.get(f"{SUPERSET_URL}/api/v1/dataset/")
    if response.status_code == 200:
        datasets = response.json()['result']
        print(f"📊 Datasets: {len(datasets)}件")
        for ds in datasets:
            print(f"  - {ds['table_name']} (ID: {ds['id']}, SQL: {ds.get('sql', 'N/A')[:50]}...)")
    else:
        print(f"❌ Dataset取得失敗: {response.status_code}")

def check_charts():
    """Chart一覧を確認"""
    response = session.get(f"{SUPERSET_URL}/api/v1/chart/")
    if response.status_code == 200:
        charts = response.json()['result']
        print(f"\n📈 Charts: {len(charts)}件")
        for chart in charts:
            print(f"  - {chart['slice_name']} (ID: {chart['id']}, Type: {chart['viz_type']})")
    else:
        print(f"❌ Chart取得失敗: {response.status_code}")

def check_dashboards():
    """Dashboard一覧を確認"""
    response = session.get(f"{SUPERSET_URL}/api/v1/dashboard/")
    if response.status_code == 200:
        dashboards = response.json()['result']
        print(f"\n📋 Dashboards: {len(dashboards)}件")
        for db in dashboards:
            print(f"  - {db['dashboard_title']} (ID: {db['id']})")
    else:
        print(f"❌ Dashboard取得失敗: {response.status_code}")

if __name__ == "__main__":
    print("=" * 60)
    print("Superset 状態確認")
    print("=" * 60)
    print()

    if login():
        check_datasets()
        check_charts()
        check_dashboards()
