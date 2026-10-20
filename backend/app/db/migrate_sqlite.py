from sqlalchemy import inspect, text

from app.db.session import engine


def ensure_sqlite_device_columns() -> None:
    """Add new columns on existing SQLite DBs (create_all does not ALTER)."""
    if engine.dialect.name != "sqlite":
        return

    desired = {
        "devices": {
            "audit_status": "VARCHAR(32) DEFAULT 'pending_audit'",
            "resident_location": "VARCHAR(255)",
            "division": "VARCHAR(255)",
            "issued_to": "VARCHAR(255)",
            "issued_to_email": "VARCHAR(255)",
            "project_manager": "VARCHAR(255)",
            "project_name": "VARCHAR(255)",
            "is_latest_model": "BOOLEAN DEFAULT 0",
            "date_of_return": "DATE",
            "notes": "TEXT",
        },
        "assignment_history": {
            "from_issued_to": "VARCHAR(255)",
            "to_issued_to": "VARCHAR(255)",
            "project_name": "VARCHAR(255)",
            "project_manager": "VARCHAR(255)",
            "division": "VARCHAR(255)",
            "resident_location": "VARCHAR(255)",
            "audit_status": "VARCHAR(32)",
            "date_of_return": "DATE",
            "notes": "TEXT",
        },
    }

    with engine.begin() as conn:
        for table_name, columns in desired.items():
            if not inspect(conn).has_table(table_name):
                continue
            existing = {col["name"] for col in inspect(conn).get_columns(table_name)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl}"))
