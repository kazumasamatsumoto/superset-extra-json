#!/usr/bin/env python3
"""
Superset Cross-Filter Dashboard自動作成スクリプト

期間検索 → ステータス計算 → 円グラフ → テーブルのクロスフィルター機能を実装
"""

import requests
import json
import time

# Superset設定
SUPERSET_URL = "http://localhost:8088"
USERNAME = "admin"
PASSWORD = "admin"

# セッション
session = requests.Session()

def login():
    """Supersetにログイン"""
    print("🔐 Supersetにログイン中...")

    # ログイン
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
        "provider": "db",
    }

    response = session.post(
        f"{SUPERSET_URL}/api/v1/security/login",
        json=login_data,
    )

    if response.status_code == 200:
        result = response.json()
        access_token = result['access_token']

        # CSRFトークン取得
        csrf_response = session.get(
            f"{SUPERSET_URL}/api/v1/security/csrf_token/",
            headers={'Authorization': f'Bearer {access_token}'}
        )

        csrf_token = None
        if csrf_response.status_code == 200:
            csrf_token = csrf_response.json().get('result')

        session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token if csrf_token else '',
            'Referer': SUPERSET_URL,
        })
        print("✅ ログイン成功")
        return True
    else:
        print(f"❌ ログイン失敗: {response.status_code}")
        print(response.text)
        return False

def get_database_id():
    """Database IDを取得"""
    print("🔍 Database IDを取得中...")

    response = session.get(f"{SUPERSET_URL}/api/v1/database/")

    if response.status_code == 200:
        databases = response.json()['result']
        # 'Main Database' または 'superset' を探す
        for db in databases:
            if db['database_name'] in ['Main Database', 'superset']:
                print(f"✅ Database ID: {db['id']} ({db['database_name']})")
                return db['id']

    print("❌ Database が見つかりません")
    return None

def create_dataset(database_id):
    """Virtual Datasetを作成"""
    print("📊 Dataset 'orders_with_status' を作成中...")

    # 既存のDatasetを確認
    response = session.get(
        f"{SUPERSET_URL}/api/v1/dataset/",
        params={"q": json.dumps({"filters": [{"col": "table_name", "opr": "eq", "value": "orders_with_status"}]})}
    )

    if response.status_code == 200 and response.json()['count'] > 0:
        dataset_id = response.json()['result'][0]['id']
        print(f"ℹ️  Dataset already exists (ID: {dataset_id})")
        return dataset_id

    # Dataset作成
    dataset_data = {
        "database": database_id,
        "schema": "public",
        "table_name": "orders_with_status",
        "sql": """
SELECT
    order_id,
    order_date,
    amount,
    customer_name,
    department_id,
    CASE
        WHEN (CURRENT_DATE - order_date) < 7 THEN '新規'
        WHEN (CURRENT_DATE - order_date) < 30 THEN '進行中'
        ELSE '遅延'
    END AS status,
    (CURRENT_DATE - order_date) AS days_since_order
FROM orders
ORDER BY order_date DESC
        """.strip(),
    }

    response = session.post(
        f"{SUPERSET_URL}/api/v1/dataset/",
        json=dataset_data,
    )

    if response.status_code == 201:
        dataset_id = response.json()['id']
        print(f"✅ Dataset作成成功 (ID: {dataset_id})")

        # Datasetを更新してカラム情報を取得
        time.sleep(1)
        refresh_response = session.put(
            f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}/refresh"
        )
        print(f"🔄 Dataset更新: {refresh_response.status_code}")

        return dataset_id
    else:
        print(f"❌ Dataset作成失敗: {response.status_code}")
        print(response.text)
        return None

def create_pie_chart(dataset_id):
    """円グラフ（ステータス別売上）を作成"""
    print("🥧 円グラフを作成中...")

    chart_data = {
        "slice_name": "ステータス別売上（円グラフ）",
        "viz_type": "pie",
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": json.dumps({
            "datasource": f"{dataset_id}__table",
            "viz_type": "pie",
            "slice_id": None,
            "groupby": ["status"],
            "metric": {
                "expressionType": "SIMPLE",
                "column": {
                    "column_name": "amount",
                    "type": "NUMERIC"
                },
                "aggregate": "SUM",
                "label": "SUM(amount)"
            },
            "adhoc_filters": [],
            "row_limit": 10000,
            "color_scheme": "supersetColors",
            "show_labels": True,
            "show_legend": True,
            "label_type": "key_value",
            "number_format": "SMART_NUMBER",
            "date_format": "smart_date",
            "show_labels_threshold": 5,
            "sort_by_metric": True,
        }),
    }

    response = session.post(
        f"{SUPERSET_URL}/api/v1/chart/",
        json=chart_data,
    )

    if response.status_code == 201:
        chart_id = response.json()['id']
        print(f"✅ 円グラフ作成成功 (ID: {chart_id})")
        return chart_id
    else:
        print(f"❌ 円グラフ作成失敗: {response.status_code}")
        print(response.text)
        return None

def create_table_chart(dataset_id):
    """テーブルチャート（詳細データ）を作成"""
    print("📋 テーブルチャートを作成中...")

    chart_data = {
        "slice_name": "受注詳細テーブル",
        "viz_type": "table",
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": json.dumps({
            "datasource": f"{dataset_id}__table",
            "viz_type": "table",
            "slice_id": None,
            "query_mode": "raw",
            "groupby": [],
            "all_columns": [
                "order_id",
                "order_date",
                "customer_name",
                "amount",
                "status",
                "days_since_order"
            ],
            "adhoc_filters": [],
            "order_by_cols": [["order_date", False]],  # Descending
            "row_limit": 100,
            "table_timestamp_format": "smart_date",
            "show_cell_bars": True,
            "color_pn": True,
        }),
    }

    response = session.post(
        f"{SUPERSET_URL}/api/v1/chart/",
        json=chart_data,
    )

    if response.status_code == 201:
        chart_id = response.json()['id']
        print(f"✅ テーブルチャート作成成功 (ID: {chart_id})")
        return chart_id
    else:
        print(f"❌ テーブルチャート作成失敗: {response.status_code}")
        print(response.text)
        return None

def create_dashboard(pie_chart_id, table_chart_id):
    """Dashboardを作成"""
    print("📊 Dashboardを作成中...")

    # Dashboard作成
    dashboard_data = {
        "dashboard_title": "受注ステータス分析（クロスフィルター）",
        "published": True,
    }

    response = session.post(
        f"{SUPERSET_URL}/api/v1/dashboard/",
        json=dashboard_data,
    )

    if response.status_code != 201:
        print(f"❌ Dashboard作成失敗: {response.status_code}")
        print(response.text)
        return None

    dashboard_id = response.json()['id']
    print(f"✅ Dashboard作成成功 (ID: {dashboard_id})")

    # Dashboard JSONを構築
    position_json = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {
            "type": "GRID",
            "id": "GRID_ID",
            "children": [
                "ROW-pie",
                "ROW-table"
            ],
            "parents": ["ROOT_ID"]
        },
        "ROW-pie": {
            "type": "ROW",
            "id": "ROW-pie",
            "children": ["CHART-pie"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"}
        },
        "CHART-pie": {
            "type": "CHART",
            "id": "CHART-pie",
            "children": [],
            "meta": {
                "width": 12,
                "height": 50,
                "chartId": pie_chart_id,
                "sliceName": "ステータス別売上（円グラフ）"
            }
        },
        "ROW-table": {
            "type": "ROW",
            "id": "ROW-table",
            "children": ["CHART-table"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"}
        },
        "CHART-table": {
            "type": "CHART",
            "id": "CHART-table",
            "children": [],
            "meta": {
                "width": 12,
                "height": 50,
                "chartId": table_chart_id,
                "sliceName": "受注詳細テーブル"
            }
        }
    }

    # Dashboard更新（レイアウト設定）
    update_data = {
        "position_json": json.dumps(position_json),
        "json_metadata": json.dumps({
            "timed_refresh_immune_slices": [],
            "expanded_slices": {},
            "refresh_frequency": 0,
            "default_filters": "{}",
            "color_scheme": "",
            "label_colors": {},
            "shared_label_colors": {},
            "cross_filters_enabled": True,  # Cross-Filter有効化
        }),
    }

    response = session.put(
        f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}",
        json=update_data,
    )

    if response.status_code == 200:
        print(f"✅ Dashboardレイアウト設定成功")
    else:
        print(f"⚠️  Dashboardレイアウト設定失敗: {response.status_code}")
        print(response.text)

    return dashboard_id

def create_native_filter(dashboard_id, dataset_id):
    """Native Filter（期間フィルター）を作成"""
    print("🔍 期間フィルターを作成中...")

    # Dashboard情報を取得
    response = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}")

    if response.status_code != 200:
        print(f"❌ Dashboard情報取得失敗: {response.status_code}")
        return False

    dashboard_data = response.json()['result']

    # Native Filterを追加
    native_filter_config = {
        "NATIVE_FILTER-1": {
            "id": "NATIVE_FILTER-1",
            "name": "期間フィルター",
            "filterType": "filter_time",
            "targets": [
                {
                    "datasetId": dataset_id,
                    "column": {
                        "name": "order_date"
                    }
                }
            ],
            "defaultDataMask": {
                "filterState": {
                    "value": "Last 30 days"
                }
            },
            "controlValues": {
                "enableEmptyFilter": False,
                "defaultToFirstItem": False,
                "multiSelect": False,
                "searchAllOptions": False,
                "inverseSelection": False
            },
            "cascadeParentIds": [],
            "scope": {
                "rootPath": ["ROOT_ID"],
                "excluded": []
            },
            "isInstant": True,
            "allowsMultipleValues": False,
            "isRequired": False
        }
    }

    # JSON metadata更新
    json_metadata = json.loads(dashboard_data.get('json_metadata', '{}'))
    json_metadata['native_filter_configuration'] = list(native_filter_config.values())

    update_data = {
        "json_metadata": json.dumps(json_metadata)
    }

    response = session.put(
        f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}",
        json=update_data,
    )

    if response.status_code == 200:
        print(f"✅ 期間フィルター作成成功")
        return True
    else:
        print(f"⚠️  期間フィルター作成失敗: {response.status_code}")
        print(response.text)
        return False

def main():
    """メイン処理"""
    print("=" * 60)
    print("Superset Cross-Filter Dashboard 自動作成")
    print("=" * 60)
    print()

    # ログイン
    if not login():
        return

    # Database ID取得
    database_id = get_database_id()
    if not database_id:
        return

    # Dataset作成
    dataset_id = create_dataset(database_id)
    if not dataset_id:
        return

    time.sleep(2)  # Dataset準備待機

    # Chart作成
    pie_chart_id = create_pie_chart(dataset_id)
    if not pie_chart_id:
        return

    table_chart_id = create_table_chart(dataset_id)
    if not table_chart_id:
        return

    time.sleep(1)

    # Dashboard作成
    dashboard_id = create_dashboard(pie_chart_id, table_chart_id)
    if not dashboard_id:
        return

    time.sleep(1)

    # Native Filter作成
    create_native_filter(dashboard_id, dataset_id)

    print()
    print("=" * 60)
    print("✅ すべての作成が完了しました！")
    print("=" * 60)
    print()
    print(f"📊 Dashboard URL:")
    print(f"   {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
    print()
    print("🎯 動作確認:")
    print("   1. 期間フィルターで 'Last 30 days' を選択")
    print("   2. 円グラフのセグメント（例: '進行中'）をクリック")
    print("   3. テーブルに該当ステータスのデータのみ表示されることを確認")
    print()

if __name__ == "__main__":
    main()
