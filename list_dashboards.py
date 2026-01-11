#!/usr/bin/env python3
"""
既存のダッシュボード一覧を取得するスクリプト
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
        return True
    return False

def list_dashboards():
    """Dashboard一覧を取得"""
    response = session.get(f"{SUPERSET_URL}/api/v1/dashboard/")

    if response.status_code == 200:
        dashboards = response.json()['result']
        print(f"📊 Dashboard一覧 ({len(dashboards)}件):")
        print()
        for db in dashboards:
            print(f"  ID: {db['id']}")
            print(f"  Title: {db['dashboard_title']}")
            print(f"  URL: {SUPERSET_URL}/superset/dashboard/{db['id']}/")
            print()
    else:
        print(f"❌ Dashboard取得失敗: {response.status_code}")

if __name__ == "__main__":
    if login():
        list_dashboards()
