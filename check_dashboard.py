#!/usr/bin/env python3
"""
作成したDashboardを確認するスクリプト
"""

from playwright.sync_api import sync_playwright
import time

SUPERSET_URL = "http://localhost:8088"
DASHBOARD_ID = 13

def check_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Supersetにログイン
        print("🔐 Supersetにログイン中...")
        page.goto(f"{SUPERSET_URL}/login/")
        page.fill('input[name="username"]', 'admin')
        page.fill('input[name="password"]', 'admin')
        page.click('button[type="submit"]')

        # ログイン完了を待つ
        time.sleep(3)

        # Dashboardにアクセス
        print(f"📊 Dashboard {DASHBOARD_ID} にアクセス中...")
        page.goto(f"{SUPERSET_URL}/superset/dashboard/{DASHBOARD_ID}/")

        # Dashboard読み込み待機
        print("⏳ Dashboard読み込み待機中...")
        time.sleep(8)

        # スクリーンショット撮影
        screenshot_path = f"dashboard-{DASHBOARD_ID}-initial.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"📸 スクリーンショット保存: {screenshot_path}")

        # Chart情報を取得
        print("\n📊 Dashboard情報:")

        # 円グラフの確認
        pie_chart = page.query_selector('text=ステータス別売上')
        if pie_chart:
            print("  ✅ 円グラフ: 表示されています")
        else:
            print("  ❌ 円グラフ: 見つかりません")

        # テーブルの確認
        table_chart = page.query_selector('text=受注詳細テーブル')
        if table_chart:
            print("  ✅ テーブル: 表示されています")
        else:
            print("  ❌ テーブル: 見つかりません")

        # データの確認
        time.sleep(2)

        # ステータスの表示を確認
        statuses = ['新規', '進行中', '遅延']
        for status in statuses:
            if page.query_selector(f'text={status}'):
                print(f"  ✅ ステータス '{status}' が表示されています")

        print("\n🎯 Cross-Filter テスト:")
        print("  手動で円グラフのセグメントをクリックして、テーブルがフィルタリングされるか確認してください")

        # ブラウザを開いたまま待機
        print("\n⏸️  ブラウザを開いたままにします。確認後、Enterキーを押してください...")
        input()

        browser.close()

if __name__ == "__main__":
    check_dashboard()
