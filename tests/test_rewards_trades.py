from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.hq import _product_quote
from app.models import Chore, ChoreTrade, PointTransaction, PurchaseRequest, User
from app.services import add_points, point_balance


class RewardsAndTradesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.app = create_app({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{root / 'test.db'}",
            "BACKUP_DIR": str(root / "backups"),
            "EXPORT_DIR": str(root / "exports"),
            "UPLOAD_DIR": str(root / "uploads"),
            "CHORE_PROOF_DIR": str(root / "uploads" / "proofs"),
            "AUTO_BACKUP_DATABASE": False,
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            self.zara = db.session.scalar(db.select(User).where(User.name == "Zara")).id
            self.aria = db.session.scalar(db.select(User).where(User.name == "Aria")).id
            self.parent = db.session.scalar(db.select(User).where(User.name == "Samantha")).id
            db.session.query(ChoreTrade).delete()
            db.session.query(PurchaseRequest).delete()
            db.session.query(Chore).delete()
            db.session.query(PointTransaction).delete()
            db.session.commit()
            add_points(self.zara, 500, "test seed", "test", None, self.parent)
            basement = Chore(task_date=date.today(), title="📦 Basement", assigned_to=self.zara, points=3, weight=3)
            laundry = Chore(task_date=date.today(), title="🧺 Laundry", assigned_to=self.zara, points=2, weight=2)
            db.session.add_all([basement, laundry])
            db.session.commit()
            self.basement_id = basement.id
            self.laundry_id = laundry.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
        self.temp_dir.cleanup()

    def login(self, user_id: int):
        with self.client.session_transaction() as sess:
            sess.clear()
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True

    def test_reward_quote_is_one_point_per_dollar_and_capped_at_350(self):
        with patch("app.hq._safe_product_url", side_effect=lambda value: value), patch("app.hq.urlopen", side_effect=OSError("offline")):
            quote = _product_quote("https://example.com/item", 8.25)
            capped = _product_quote("https://example.com/expensive", 999.99)
        self.assertEqual(quote["points"], 9)
        self.assertEqual(capped["points"], 350)

    def test_purchase_request_spends_points_then_denial_refunds(self):
        self.login(self.zara)
        with self.app.app_context():
            quote = PurchaseRequest(
                user_id=self.zara,
                product_url="https://example.com/item",
                product_title="Example Item",
                price_cents=1250,
                cost_points=13,
                status="quoted",
            )
            db.session.add(quote)
            db.session.commit()
            quote_id = quote.id
        with self.client.session_transaction() as sess:
            sess["reward_quote_id"] = quote_id
        response = self.client.post("/household/rewards/request", data={"note": "please"})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            item = db.session.scalar(db.select(PurchaseRequest))
            self.assertIsNotNone(item)
            self.assertEqual(item.cost_points, 13)
            self.assertEqual(point_balance(self.zara), 487)
            purchase_id = item.id

        self.login(self.parent)
        response = self.client.post(f"/household/purchases/{purchase_id}/resolve", data={"status": "denied"})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            item = db.session.get(PurchaseRequest, purchase_id)
            self.assertEqual(item.status, "denied")
            self.assertEqual(point_balance(self.zara), 500)


    def test_product_link_is_hidden_from_child_and_visible_to_parent(self):
        self.login(self.zara)
        with self.app.app_context():
            quote = PurchaseRequest(
                user_id=self.zara,
                product_url="https://example.com/private-wish",
                product_title="Private Wish",
                price_cents=2000,
                cost_points=20,
                status="quoted",
            )
            db.session.add(quote)
            db.session.commit()
            quote_id = quote.id
        with self.client.session_transaction() as sess:
            sess["reward_quote_id"] = quote_id
        self.client.post("/household/rewards/request", data={"note": "please"})
        child_page = self.client.get("/household")
        self.assertNotIn(b"https://example.com/private-wish", child_page.data)
        self.assertIn(b"Link visible to parents only", child_page.data)

        self.login(self.parent)
        parent_page = self.client.get("/household")
        self.assertIn(b"https://example.com/private-wish", parent_page.data)
        self.assertIn(b"Open private purchase link", parent_page.data)

    def test_paired_chore_trade_moves_both_chores_and_transfers_escrow(self):
        self.login(self.zara)
        response = self.client.post("/household/chore-trades/create", data={
            "chore_id": self.basement_id,
            "offered_points": 40,
            "requested_to": self.aria,
            "note": "take this pair",
        })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            trade = db.session.scalar(db.select(ChoreTrade))
            self.assertEqual(set(trade.parsed_chore_ids()), {self.basement_id, self.laundry_id})
            self.assertEqual(point_balance(self.zara), 460)
            trade_id = trade.id

        self.login(self.aria)
        response = self.client.post(f"/household/chore-trades/{trade_id}/accept")
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            trade = db.session.get(ChoreTrade, trade_id)
            self.assertEqual(trade.status, "accepted")
            self.assertEqual(db.session.get(Chore, self.basement_id).assigned_to, self.aria)
            self.assertEqual(db.session.get(Chore, self.laundry_id).assigned_to, self.aria)
            self.assertEqual(point_balance(self.aria), 40)
            self.assertEqual(point_balance(self.zara), 460)

    def test_household_page_exposes_new_exchange_and_link_store(self):
        self.login(self.zara)
        response = self.client.get("/household")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Link Rewards Store", response.data)
        self.assertIn(b"maximum 350 points", response.data)
        self.assertIn(b"Chore Trade Exchange", response.data)
        self.assertIn(b"Basement + Laundry", response.data)


if __name__ == "__main__":
    unittest.main()
