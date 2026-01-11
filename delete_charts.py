#!/usr/bin/env python3
"""
不要なChartを削除するスクリプト
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

def list_all_charts():
    """全Chart一覧を表示"""
    print("\n📊 Chart一覧:")
    print("-" * 60)

    # データベースから直接取得
    import subprocess
    result = subprocess.run(
        ['docker', 'exec', 'superset_app', 'psql', '-U', 'superset', '-d', 'superset',
         '-c', 'SELECT id, slice_name, viz_type FROM slices ORDER BY id;'],
        env={'DOCKER_HOST': f'unix://{os.path.expanduser("~")}/.docker/run/docker.sock'},
        capture_output=True,
        text=True
    )
    print(result.stdout)

def delete_chart(chart_id):
    """指定されたChartを削除"""
    print(f"\n🗑️  Chart ID {chart_id} を削除中...")
    response = session.delete(f"{SUPERSET_URL}/api/v1/chart/{chart_id}")

    if response.status_code == 200:
        print(f"✅ Chart ID {chart_id} を削除しました")
        return True
    else:
        print(f"❌ 削除失敗: {response.status_code}")
        print(f"Response: {response.text}")
        return False

if __name__ == "__main__":
    import os

    print("=" * 60)
    print("Chart削除ツール")
    print("=" * 60)

    if login():
        list_all_charts()

        print("\n削除したいChart IDをカンマ区切りで入力してください (例: 1,2,3)")
        print("または 'all' で全Chart削除:")

        user_input = input("> ").strip()

        if user_input.lower() == 'all':
            confirm = input("本当に全Chartを削除しますか? (yes/no): ")
            if confirm.lower() == 'yes':
                # すべてのChart IDを取得して削除
                result = subprocess.run(
                    ['docker', 'exec', 'superset_app', 'psql', '-U', 'superset', '-d', 'superset',
                     '-t', '-c', 'SELECT id FROM slices;'],
                    env={'DOCKER_HOST': f'unix://{os.path.expanduser("~")}/.docker/run/docker.sock'},
                    capture_output=True,
                    text=True
                )
                chart_ids = [int(x.strip()) for x in result.stdout.strip().split('\n') if x.strip()]
                for chart_id in chart_ids:
                    delete_chart(chart_id)
        else:
            chart_ids = [int(x.strip()) for x in user_input.split(',') if x.strip()]
            for chart_id in chart_ids:
                delete_chart(chart_id)

        print("\n✅ 完了")
