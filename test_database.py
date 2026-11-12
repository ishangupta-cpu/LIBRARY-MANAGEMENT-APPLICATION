"""Small automated checks for the SQLite data layer (run with: python -m unittest)."""

import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["LIBRARY_DB_PATH"] = str(Path(self.temp_dir.name) / "test_library.db")
        import database
        self.database = database
        database.initialize_database()

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("LIBRARY_DB_PATH", None)

    def test_add_and_list_book(self):
        self.database.add_book(" Python Basics ", " Ada Lovelace ", "Programming", 3)
        book = self.database.get_books()[0]
        self.assertEqual(book["book_title"], "Python Basics")
        self.assertEqual(book["author_name"], "Ada Lovelace")
        self.assertEqual(book["available_copies"], 3)

    def test_statistics(self):
        self.database.add_book("Python", "Ada", "Programming", 3)
        self.database.add_book("AI", "Alan", "Artificial Intelligence", 5)
        self.assertEqual(self.database.get_total_copies(), 8)
        self.assertEqual(self.database.get_most_available_book()["book_title"], "AI")
        summary = {row["category"]: row for row in self.database.get_category_summary()}
        self.assertEqual(summary["Programming"]["title_count"], 1)
        self.assertEqual(summary["Programming"]["total_copies"], 3)

    def test_validation_rejects_missing_title_and_zero_copies(self):
        with self.assertRaises(ValueError):
            self.database.add_book(" ", "Author", "Programming", 1)
        with self.assertRaises(ValueError):
            self.database.add_book("Title", "Author", "Programming", 0)

    def test_update_and_delete_book(self):
        self.database.add_book("Old title", "Author", "Programming", 2)
        book = self.database.get_books()[0]
        self.database.update_book(book["book_id"], "New title", "New author", "Mathematics", 4)
        updated = self.database.get_books()[0]
        self.assertEqual(updated["book_title"], "New title")
        self.assertEqual(updated["available_copies"], 4)
        self.database.delete_book(book["book_id"])
        self.assertEqual(self.database.get_books(), [])

    def test_borrow_and_return_adjusts_available_copies(self):
        self.database.add_book("Python", "Ada", "Programming", 1)
        book = self.database.get_books()[0]
        today = date.today()
        due = (today + timedelta(days=7)).isoformat()
        self.database.borrow_book(book["book_id"], "Student One", due, today.isoformat())
        self.assertEqual(self.database.get_books()[0]["available_copies"], 0)
        self.assertEqual(self.database.get_active_loan_count(), 1)
        with self.assertRaises(ValueError):
            self.database.delete_book(book["book_id"])
        active_loan = self.database.get_loans(active_only=True)[0]
        self.database.return_book(active_loan["loan_id"], today.isoformat())
        self.assertEqual(self.database.get_books()[0]["available_copies"], 1)
        self.assertEqual(self.database.get_active_loan_count(), 0)


if __name__ == "__main__":
    unittest.main()
