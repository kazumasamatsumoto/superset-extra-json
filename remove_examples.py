#!/usr/bin/env python3
"""
Remove all example dashboards, charts, and datasets from Superset
"""

import sys

# Execute this inside the Superset container
delete_script = """
from superset import app, db
from superset.models.dashboard import Dashboard
from superset.models.slice import Slice
from superset.models.core import Database

with app.app_context():
    # Delete all dashboards
    dashboards = db.session.query(Dashboard).all()
    print(f"Found {len(dashboards)} dashboards")
    for dashboard in dashboards:
        print(f"Deleting dashboard: {dashboard.dashboard_title}")
        db.session.delete(dashboard)

    # Delete all charts/slices
    slices = db.session.query(Slice).all()
    print(f"Found {len(slices)} charts")
    for slice in slices:
        print(f"Deleting chart: {slice.slice_name}")
        db.session.delete(slice)

    # Delete example databases (keep only the main superset DB)
    databases = db.session.query(Database).filter(Database.database_name != 'superset').all()
    print(f"Found {len(databases)} example databases")
    for database in databases:
        print(f"Deleting database: {database.database_name}")
        db.session.delete(database)

    db.session.commit()
    print("All examples removed successfully!")
"""

print(delete_script)
