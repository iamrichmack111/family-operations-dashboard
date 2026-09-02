import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("FAMILY_DASHBOARD_HOST", "0.0.0.0"),
        port=int(os.environ.get("FAMILY_DASHBOARD_PORT", "8011")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
