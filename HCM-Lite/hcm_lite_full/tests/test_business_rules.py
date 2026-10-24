"""Small isolated smoke tests for core HCM rules. Run: python -m unittest discover -s tests"""
import tempfile
import unittest
from pathlib import Path
from datetime import date
import backend.db as db

class HCMRuleTests(unittest.TestCase):
    def setUp(self):
        self.original_path = db.DB_PATH
        db.DB_PATH = Path(tempfile.gettempdir()) / f"hcm_test_{id(self)}.sqlite3"
        db.DB_PATH.unlink(missing_ok=True)
        db.init_db()
        db.create_admin_if_needed()
        db.add_department("Engineering", "Analyst")
        db.create_employee("T001", "Test Person", "test.person@example.com", "Engineering", "Analyst", date.today().isoformat(), 50000, "Temporary123!")
        self.employee = db.list_employees()[0]

    def tearDown(self):
        db.DB_PATH.unlink(missing_ok=True)
        db.DB_PATH = self.original_path

    def test_duplicate_checkin_rejected(self):
        first = db.check_in(self.employee["id"])
        second = db.check_in(self.employee["id"])
        self.assertTrue(first[0])
        self.assertFalse(second[0])

    def test_leave_overlap_and_quota(self):
        ok, _ = db.submit_leave(self.employee["id"], "casual", "2026-11-02", "2026-11-03", "Family event")
        self.assertTrue(ok)
        ok2, message = db.submit_leave(self.employee["id"], "casual", "2026-11-03", "2026-11-04", "Overlapping event")
        self.assertFalse(ok2)
        self.assertIn("overlap", message.lower())

    def test_geofence_distance(self):
        self.assertAlmostEqual(db.haversine_m(24.8607, 67.0011, 24.8607, 67.0011), 0, places=3)
        self.assertGreater(db.haversine_m(24.8607, 67.0011, 24.8617, 67.0011), 100)

    def test_tax_slabs(self):
        self.assertEqual(db.tax_annual(600000), 0)
        self.assertEqual(db.tax_annual(900000), 15000)
        self.assertEqual(db.tax_annual(1500000), 75000)

if __name__ == "__main__":
    unittest.main()
