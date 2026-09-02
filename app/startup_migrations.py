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
    """Apply safe additive schema updates and return the applied migration IDs.

    The migration uses ``ALTER TABLE ... ADD COLUMN`` only. It never recreates
    or truncates a table, so existing users, PIN hashes, chores, and history are
    left untouched. The second column check handles two app workers starting at
    the same time and racing to apply the same idempotent change.
    """

    if "proof_photo_name" in _column_names("chores"):
        return []

    statement = text(
        "ALTER TABLE chores "
        "ADD COLUMN proof_photo_name VARCHAR(255) NOT NULL DEFAULT ''"
    )

    try:
        with db.engine.begin() as connection:
            connection.execute(statement)
    except SQLAlchemyError:
        if "proof_photo_name" not in _column_names("chores"):
            raise
        return []

    return ["chores.proof_photo_name"]
