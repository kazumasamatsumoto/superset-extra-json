#!/usr/bin/env python3
"""
古いDashboard用Chart (ID: 121-129) を削除
"""

import requests
import json
import time

SUPERSET_URL = "http://localhost:8088"
USERNAME = "admin"
PASSWORD = "admin"

# 削除対象のChart ID
CHART_IDS_TO_DELETE = [121, 122, 123, 124, 125, 126, 127, 128, 129]

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
    """指定されたChartを削除"""
    print(f"\n🗑️  {len(CHART_IDS_TO_DELETE)}件のChartを削除します...")
    print("-" * 60)

    deleted = 0
    failed = 0

    for chart_id in CHART_IDS_TO_DELETE:
        print(f"  Chart ID {chart_id} を削除中...", end=" ")
        response = session.delete(f"{SUPERSET_URL}/api/v1/chart/{chart_id}")

        if response.status_code == 200:
            print("✅")
            deleted += 1
        else:
            print(f"❌ ({response.status_code})")
            failed += 1

        time.sleep(0.2)  # APIレート制限対策

    print("-" * 60)
    print(f"\n結果: 削除成功 {deleted}件 / 失敗 {failed}件")

if __name__ == "__main__":
    print("=" * 60)
    print("古いChart削除")
    print("=" * 60)
    print()
    print("削除対象:")
    print("  ID 121-129 (古いDashboard用Chart)")
    print()
    print("残すChart:")
    print("  ID 130: 製品ステータス分布（円グラフ）")
    print("  ID 131: 製品テスト結果詳細（テーブル）")
    print("  ID 133: 製品別ステータス内訳（棒グラフ）")
    print()

    if login():
        delete_charts()
        print()
        print("✅ 完了")
