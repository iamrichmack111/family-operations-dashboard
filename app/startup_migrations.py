"""Small, idempotent startup migrations for bundled SQLite installations."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from .extensions import db


def _column_names(table_name: str) -> set[str]:
    inspector = inspect(db.engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def run_startup_migrations() -> list[str]:
    """Add missing columns without replacing or resetting existing household records."""
    applied = []
    columns = (
        ("chores", "proof_photo_name", "VARCHAR(255) NOT NULL DEFAULT ''"),
        ("homework", "sentence_count", "INTEGER"),
    )
    for table, column, definition in columns:
        if column in _column_names(table) or not _column_names(table):
            continue
        try:
            with db.engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
        except SQLAlchemyError:
            if column not in _column_names(table):
                raise
        applied.append(f"{table}.{column}")
    return applied
