from __future__ import annotations

import io
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from PIL import Image

from app import create_app
from app.chore_rotation import chore_assignments_for
from app.extensions import db
from app.models import Chore, PointTransaction, User
from app.services import ensure_week


def png_upload(filename: str = "proof.png") -> tuple[io.BytesIO, str]:
    buffer = io.BytesIO()
    Image.new("RGB", (48, 36), (39, 199, 255)).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer, filename


class PhotoProofWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.database_path = root / "test.db"
        self.proof_dir = root / "uploads" / "chore_proofs"
        self.app = create_app(
            {
                "TESTING": True,
                "WTF_CSRF_ENABLED": False,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path}",
                "CHORE_PROOF_DIR": str(self.proof_dir),
                "UPLOAD_DIR": str(root / "uploads"),
                "BACKUP_DIR": str(root / "backups"),
                "EXPORT_DIR": str(root / "exports"),
                "AUTO_BACKUP_DATABASE": False,
            }
        )
        self.client = self.app.test_client()

        with self.app.app_context():
            db.session.query(Chore).delete()
            db.session.query(PointTransaction).delete()
            db.session.commit()
            self.child_id = db.session.scalar(db.select(User.id).where(User.name == "Zara"))
            self.parent_id = db.session.scalar(db.select(User.id).where(User.name == "Samantha"))
            self.manager_id = db.session.scalar(db.select(User.id).where(User.name == "Jasmin"))
            chore = Chore(
                task_date=date.today(),
                title="🧽 Test the kitchen",
                assigned_to=self.child_id,
                points=5,
                weight=5,
            )
            db.session.add(chore)
            db.session.commit()
            self.chore_id = chore.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
        self.temp_dir.cleanup()

    def login(self, user_id: int) -> None:
        with self.client.session_transaction() as session:
            session.clear()
            session["_user_id"] = str(user_id)
            session["_fresh"] = True

    def chore(self) -> Chore:
        return db.session.get(Chore, self.chore_id)

    def complete_with_photo(self, filename: str = "../../unsafe family proof.png"):
        self.login(self.child_id)
        return self.client.post(
            f"/tasks/chore/{self.chore_id}/complete",
            data={"note": "Finished", "proof_photo": png_upload(filename)},
            content_type="multipart/form-data",
        )

    def test_chore_completion_is_allowed_without_photo(self):
        self.login(self.child_id)
        response = self.client.post(
            f"/tasks/chore/{self.chore_id}/complete",
            data={"note": "No photo"},
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(self.chore().status, "completed")
            self.assertEqual(self.chore().proof_photo_name, "")
            self.assertEqual(self.chore().note, "No photo")

    def test_future_chore_cannot_be_completed_early_even_with_photo(self):
        with self.app.app_context():
            future = Chore(
                task_date=date.today() + timedelta(days=1),
                title="🧭 Future preview test",
                assigned_to=self.child_id,
                points=3,
                weight=3,
            )
            db.session.add(future)
            db.session.commit()
            future_id = future.id

        self.login(self.child_id)
        response = self.client.post(
            f"/tasks/chore/{future_id}/complete",
            data={"proof_photo": png_upload()},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            future = db.session.get(Chore, future_id)
            self.assertEqual(future.status, "assigned")
            self.assertEqual(future.proof_photo_name, "")
        self.assertEqual(list(self.proof_dir.glob("*")), [])

    def test_dashboard_renders_all_seven_real_data_graphs(self):
        self.login(self.parent_id)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b"<canvas"), 7)
        for chart_id in (
            b'pointsChart',
            b'completionChart',
            b'earnedChart',
            b'workloadChart',
            b'statusChart',
            b'reviewChart',
            b'movementChart',
        ):
            self.assertIn(chart_id, response.data)
        self.assertIn(b"Household rhythm", response.data)
        self.assertIn(b"Last 30 days", response.data)
        response.close()

    def test_dashboard_shows_the_current_users_next_day_assignments(self):
        self.login(self.child_id)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your assignments tomorrow", response.data)
        self.assertIn(b'class="tomorrow-assignment"', response.data)
        self.assertIn(b'data-assignee="Zara"', response.data)
        self.assertNotIn(b'data-assignee="Jasmin"', response.data)
        self.assertNotIn(b'data-assignee="Aria"', response.data)
        self.assertIn(b"read-only preview", response.data)
        response.close()

    def test_open_future_rotation_is_reconciled_but_completed_work_is_preserved(self):
        today = date.today()
        with self.app.app_context():
            ensure_week(today)
            users = {
                user.name: user.id
                for user in db.session.scalars(db.select(User)).all()
            }

            tomorrow = today + timedelta(days=1)
            tomorrow_expected = {
                title: person
                for title, person, _points in chore_assignments_for(
                    tomorrow,
                    include_emoji=False,
                )
            }
            bathroom = db.session.scalar(
                db.select(Chore).where(
                    Chore.task_date == tomorrow,
                    Chore.title == "🛁 Bathrooms",
                )
            )
            basement = db.session.scalar(
                db.select(Chore).where(
                    Chore.task_date == tomorrow,
                    Chore.title == "📦 Basement",
                )
            )
            bathroom.assigned_to = users["Zara"]
            basement.assigned_to = users["Zara"]

            completed_day = today + timedelta(days=2)
            completed = db.session.scalar(
                db.select(Chore).where(
                    Chore.task_date == completed_day,
                    Chore.title == "🛁 Bathrooms",
                )
            )
            completed_wrong_user = next(
                name
                for name in users
                if name
                != dict(
                    (title, person)
                    for title, person, _points in chore_assignments_for(
                        completed_day,
                        include_emoji=False,
                    )
                )["Bathrooms"]
            )
            completed.assigned_to = users[completed_wrong_user]
            completed.status = "completed"
            db.session.commit()

            ensure_week(today)
            self.assertEqual(bathroom.assignee.name, tomorrow_expected["Bathrooms"])
            self.assertEqual(basement.assignee.name, tomorrow_expected["Basement"])
            laundry = db.session.scalar(
                db.select(Chore).where(
                    Chore.task_date == tomorrow,
                    Chore.title == "🧺 Laundry",
                )
            )
            kitchen = db.session.scalar(
                db.select(Chore).where(
                    Chore.task_date == tomorrow,
                    Chore.title == "🧹 Kitchen deep clean",
                )
            )
            self.assertEqual(basement.assigned_to, laundry.assigned_to)
            self.assertEqual(bathroom.assigned_to, kitchen.assigned_to)
            self.assertNotEqual(bathroom.assigned_to, basement.assigned_to)
            self.assertEqual(completed.assignee.name, completed_wrong_user)
            self.assertEqual(completed.status, "completed")

    def test_fake_or_mismatched_image_is_rejected(self):
        self.login(self.child_id)
        response = self.client.post(
            f"/tasks/chore/{self.chore_id}/complete",
            data={"proof_photo": (io.BytesIO(b"not an image"), "proof.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(self.chore().status, "assigned")
        self.assertEqual(list(self.proof_dir.glob("*")), [])

        response = self.client.post(
            f"/tasks/chore/{self.chore_id}/complete",
            data={"proof_photo": png_upload("wrong-extension.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(self.chore().status, "assigned")

    def test_valid_photo_is_reencoded_and_stored_with_safe_filename(self):
        response = self.complete_with_photo()
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            chore = self.chore()
            self.assertEqual(chore.status, "completed")
            self.assertRegex(chore.proof_photo_name, rf"^chore-{self.chore_id}-[0-9a-f]{{32}}\.png$")
            stored = self.proof_dir / chore.proof_photo_name
            self.assertTrue(stored.is_file())
            self.assertEqual(stored.parent, self.proof_dir)
            with Image.open(stored) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (48, 36))

    def test_parent_can_approve_without_photo(self):
        with self.app.app_context():
            chore = self.chore()
            chore.status = "completed"
            chore.proof_photo_name = ""
            db.session.commit()
        self.login(self.parent_id)
        page = self.client.get("/approvals")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Photos are optional", page.data)
        self.assertIn(b"No photo attached", page.data)
        self.assertNotIn(b"Approval is locked", page.data)

        response = self.client.post(
            f"/tasks/chore/{self.chore_id}/review",
            data={"status": "approved"},
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(self.chore().status, "approved")
            points = db.session.scalar(
                db.select(db.func.count(PointTransaction.id)).where(
                    PointTransaction.source_type == "chore",
                    PointTransaction.source_id == self.chore_id,
                )
            )
            self.assertEqual(points, 1)

    def test_needs_redo_and_excuse_remain_available_without_photo(self):
        with self.app.app_context():
            self.chore().status = "completed"
            db.session.commit()
        self.login(self.parent_id)
        self.client.post(
            f"/tasks/chore/{self.chore_id}/review",
            data={"status": "needs_redo", "note": "Please try again"},
        )
        with self.app.app_context():
            self.assertEqual(self.chore().status, "needs_redo")

            second = Chore(
                task_date=date.today(),
                title="🧹 Excuse test",
                assigned_to=self.child_id,
                points=3,
                weight=3,
                status="completed",
            )
            db.session.add(second)
            db.session.commit()
            second_id = second.id

        self.client.post(
            f"/tasks/chore/{second_id}/review",
            data={"status": "excused", "note": "Family exception"},
        )
        with self.app.app_context():
            self.assertEqual(db.session.get(Chore, second_id).status, "excused")

    def test_approval_page_displays_photo_and_valid_approval_awards_points(self):
        self.complete_with_photo()
        self.login(self.parent_id)
        page = self.client.get("/approvals")
        self.assertEqual(page.status_code, 200)
        self.assertIn(f"/chores/{self.chore_id}/proof".encode(), page.data)
        self.assertIn(b"<img", page.data)

        proof = self.client.get(f"/chores/{self.chore_id}/proof")
        self.assertEqual(proof.status_code, 200)
        self.assertEqual(proof.headers["X-Content-Type-Options"], "nosniff")
        self.assertTrue(proof.mimetype.startswith("image/"))
        proof.close()

        response = self.client.post(
            f"/tasks/chore/{self.chore_id}/review",
            data={"status": "approved", "note": "Looks great"},
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(self.chore().status, "approved")
            transaction = db.session.scalar(
                db.select(PointTransaction).where(
                    PointTransaction.source_type == "chore",
                    PointTransaction.source_id == self.chore_id,
                )
            )
            self.assertIsNotNone(transaction)
            self.assertEqual(transaction.amount, 5)


class AutomaticMigrationTests(unittest.TestCase):
    def test_legacy_database_is_migrated_without_changing_existing_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database = root / "legacy.db"
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL
                );
                INSERT INTO users(id, name, password_hash)
                VALUES (7, 'Existing User', 'preserve-this-pin-hash');

                CREATE TABLE chores (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                INSERT INTO chores(id, title, status)
                VALUES (11, 'Existing chore', 'completed');
                """
            )
            connection.commit()
            connection.close()

            config = {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}",
                "CHORE_PROOF_DIR": str(root / "uploads" / "chore_proofs"),
                "UPLOAD_DIR": str(root / "uploads"),
                "BACKUP_DIR": str(root / "backups"),
                "EXPORT_DIR": str(root / "exports"),
                "AUTO_BACKUP_DATABASE": False,
                "SEED_DEFAULTS": False,
            }
            create_app(config)
            create_app(config)  # The migration must also be idempotent.

            connection = sqlite3.connect(database)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(chores)")}
            user_row = connection.execute(
                "SELECT id, name, password_hash FROM users"
            ).fetchone()
            chore_row = connection.execute(
                "SELECT id, title, status, proof_photo_name FROM chores"
            ).fetchone()
            connection.close()

            self.assertIn("proof_photo_name", columns)
            self.assertEqual(user_row, (7, "Existing User", "preserve-this-pin-hash"))
            self.assertEqual(chore_row, (11, "Existing chore", "completed", ""))


if __name__ == "__main__":
    unittest.main()
