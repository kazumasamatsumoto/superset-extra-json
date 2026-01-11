#!/usr/bin/env python3
"""
Generate Guest Token for Superset Dashboard with Department Filtering
"""

import jwt
import datetime
import sys

# Superset Configuration
SUPERSET_SECRET_KEY = "TEST_NON_DEV_SECRET"  # From docker/.env
SUPERSET_URL = "http://localhost:8088"
DASHBOARD_ID = "12"  # Dashboard ID (number, not UUID)

def generate_guest_token(department_id, username):
    """
    Generate Guest Token with department_id filter

    Args:
        department_id: 部署ID (101: 営業部, 102: 開発部, 103: マーケティング部)
        username: ユーザー名

    Returns:
        tuple: (token, embed_url)
    """
    payload = {
        "user": {
            "username": username,
            "first_name": "Guest",
            "last_name": "User"
        },
        "resources": [{
            "type": "dashboard",
            "id": "7aaabc03-2c47-4540-8233-f22bbdb2cc81"  # Use embedded_dashboards UUID
        }],
        "rls": [
            {"clause": f"department_id = {department_id}"}
        ],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }

    token = jwt.encode(payload, SUPERSET_SECRET_KEY, algorithm="HS256")
    # Correct endpoint for Superset 5.0 (without /superset prefix)
    # Add standalone=true to bypass iframe check
    embed_url = f"{SUPERSET_URL}/dashboard/{DASHBOARD_ID}/embedded?guest_token={token}&standalone=true"

    return token, embed_url

if __name__ == "__main__":
    # 部署情報
    departments = [
        (101, "営業部ユーザー", "営業部"),
        (102, "開発部ユーザー", "開発部"),
        (103, "マーケティング部ユーザー", "マーケティング部")
    ]

    print("=" * 100)
    print("Superset Guest Token Generator - 部署別フィルタリング検証")
    print("=" * 100)
    print()

    for dept_id, user_name, dept_name in departments:
        token, url = generate_guest_token(dept_id, user_name)

        print(f"【{dept_name}】")
        print(f"  部署ID: {dept_id}")
        print(f"  ユーザー名: {user_name}")
        print(f"  Token: {token}")
        print(f"  URL: {url}")
        print("-" * 100)
        print()

    print("\n【検証手順】")
    print("1. 上記のURLをそれぞれブラウザで開く")
    print("2. 各URLで表示されるデータが部署ごとに異なることを確認")
    print("   - 営業部 (101): 営業部のデータのみ表示")
    print("   - 開発部 (102): 開発部のデータのみ表示")
    print("   - マーケティング部 (103): マーケティング部のデータのみ表示")
    print()
    print("【期待される売上合計】")
    print("  営業部 (101): ¥955,000")
    print("  開発部 (102): ¥825,000")
    print("  マーケティング部 (103): ¥240,000")
    print()
