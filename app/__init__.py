from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from flask import Flask

from .extensions import csrf, db, login_manager, migrate
from .services import backup_database, seed_defaults


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    database_path = Path(app.instance_path) / "family_dashboard.db"
    project_root = Path(app.root_path).parent
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FAMILY_DASHBOARD_SECRET", "change-this-before-production"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", f"sqlite:///{database_path}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        EXPORT_DIR=str(project_root / "exports"),
        BACKUP_DIR=str(project_root / "backups"),
        UPLOAD_DIR=str(project_root / "uploads"),
        MAX_CONTENT_LENGTH=12 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=60),
    )
    if test_config:
        app.config.update(test_config)
    for folder in (app.instance_path, app.config["EXPORT_DIR"], app.config["BACKUP_DIR"], app.config["UPLOAD_DIR"]):
        Path(folder).mkdir(parents=True, exist_ok=True)
    db.init_app(app); migrate.init_app(app, db); login_manager.init_app(app); csrf.init_app(app)
    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .parent import bp as parent_bp
    app.register_blueprint(auth_bp); app.register_blueprint(main_bp); app.register_blueprint(parent_bp)
    with app.app_context():
        db.create_all(); seed_defaults(); backup_database()
    return app
