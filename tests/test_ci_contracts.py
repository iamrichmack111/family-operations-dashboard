"""Fast deterministic CI contracts for the current family-dashboard build.

These tests deliberately use only the Python standard library.  They protect
important product rules without depending on browser rendering, Pillow codec
behavior, DNS, or a live product page.
"""
from __future__ import annotations

import re
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CurrentBuildContracts(unittest.TestCase):
    def test_reward_pricing_contract_is_three_points_per_dollar_with_350_cap(self):
        source = (ROOT / "app" / "hq.py").read_text(encoding="utf-8")
        self.assertRegex(source, r"REWARD_POINTS_PER_DOLLAR\s*=\s*3\b")
        self.assertRegex(source, r"REWARD_MAX_POINTS\s*=\s*350\b")
        self.assertIn("math.ceil(price * REWARD_POINTS_PER_DOLLAR)", source)

    def test_parent_only_purchase_link_contract_is_present(self):
        template = (ROOT / "app" / "templates" / "household.html").read_text(encoding="utf-8")
        self.assertIn("{% if current_user.is_parent %}", template)
        self.assertIn("item.product_url", template)
        self.assertIn("Link visible to parents only", template)

    def test_optional_photo_contract_is_present(self):
        main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
        approvals = (ROOT / "app" / "templates" / "approvals.html").read_text(encoding="utf-8")
        # Completion only processes a photo when a filename was actually supplied.
        self.assertIn("if upload is not None and upload.filename:", main)
        self.assertIn("Photos are optional", approvals)

    def test_bundled_database_integrity(self):
        db_path = ROOT / "instance" / "family_dashboard.db"
        if not db_path.exists():
            self.skipTest("No bundled SQLite database in this source/production checkout")
        with sqlite3.connect(db_path) as con:
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(con.execute("SELECT COUNT(*) FROM users").fetchone()[0], 5)

    def test_rotation_source_excludes_parent_accounts(self):
        source = (ROOT / "app" / "chore_rotation.py").read_text(encoding="utf-8")
        match = re.search(r"PEOPLE\s*=\s*\(([^\n]+)\)", source)
        self.assertIsNotNone(match)
        members = match.group(1)
        self.assertIn('"Zara"', members)
        self.assertIn('"Jasmin"', members)
        self.assertIn('"Aria"', members)
        self.assertNotIn('"Jeremy"', members)
        self.assertNotIn('"Samantha"', members)


if __name__ == "__main__":
    unittest.main()
