"""SQLite storage helpers for the library inventory and borrowing log."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path


def get_connection():
    """Open a connection and return rows that can be read by column name."""
    db_path = Path(os.environ.get("LIBRARY_DB_PATH", Path(__file__).with_name("library.db")))
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create or update the tables when the app starts."""
    with closing(get_connection()) as connection, connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS books (
                book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_title TEXT NOT NULL,
                author_name TEXT NOT NULL,
                category TEXT NOT NULL,
                available_copies INTEGER NOT NULL CHECK (available_copies >= 0)
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS loans (
                loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL REFERENCES books(book_id) ON DELETE RESTRICT,
                borrower_name TEXT NOT NULL,
                borrowed_on TEXT NOT NULL,
                due_date TEXT NOT NULL,
                returned_on TEXT
            )
        """)


def add_book(book_title, author_name, category, available_copies):
    """Validate and save one book record."""
    title, author, category = book_title.strip(), author_name.strip(), category.strip()
    if not title or not author or not category:
        raise ValueError("Title, author, and category are required.")
    if isinstance(available_copies, bool) or int(available_copies) != available_copies or available_copies < 1:
        raise ValueError("Available copies must be a whole number of at least 1.")
    with closing(get_connection()) as connection, connection:
        connection.execute(
            "INSERT INTO books (book_title, author_name, category, available_copies) VALUES (?, ?, ?, ?)",
            (title, author, category, int(available_copies)),
        )


def update_book(book_id, book_title, author_name, category, available_copies):
    """Update the descriptive details or available stock for a title."""
    title, author, category = book_title.strip(), author_name.strip(), category.strip()
    if not title or not author or not category:
        raise ValueError("Title, author, and category are required.")
    if isinstance(available_copies, bool) or int(available_copies) != available_copies or available_copies < 0:
        raise ValueError("Available copies must be a whole number of zero or more.")
    with closing(get_connection()) as connection, connection:
        result = connection.execute(
            "UPDATE books SET book_title = ?, author_name = ?, category = ?, available_copies = ? WHERE book_id = ?",
            (title, author, category, int(available_copies), book_id),
        )
        if result.rowcount == 0:
            raise ValueError("That book could not be found.")


def delete_book(book_id):
    """Delete a title if it has no borrowing history."""
    with closing(get_connection()) as connection, connection:
        loan_count = connection.execute(
            "SELECT COUNT(*) FROM loans WHERE book_id = ?", (book_id,)
        ).fetchone()[0]
        if loan_count:
            raise ValueError("This book has borrowing history and cannot be removed. You can still edit its details.")
        result = connection.execute("DELETE FROM books WHERE book_id = ?", (book_id,))
        if result.rowcount == 0:
            raise ValueError("That book could not be found.")


def get_books():
    with closing(get_connection()) as connection, connection:
        rows = connection.execute(
            "SELECT book_id, book_title, author_name, category, available_copies FROM books "
            "ORDER BY book_title COLLATE NOCASE, author_name COLLATE NOCASE"
        ).fetchall()
    return [dict(row) for row in rows]


def get_total_copies():
    with closing(get_connection()) as connection, connection:
        return connection.execute("SELECT COALESCE(SUM(available_copies), 0) FROM books").fetchone()[0]


def get_most_available_book():
    with closing(get_connection()) as connection, connection:
        row = connection.execute(
            "SELECT book_id, book_title, author_name, category, available_copies FROM books "
            "ORDER BY available_copies DESC, book_title COLLATE NOCASE LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def get_category_summary():
    with closing(get_connection()) as connection, connection:
        rows = connection.execute(
            "SELECT category, COUNT(*) AS title_count, SUM(available_copies) AS total_copies "
            "FROM books GROUP BY category ORDER BY category COLLATE NOCASE"
        ).fetchall()
    return [dict(row) for row in rows]


def get_active_loan_count():
    with closing(get_connection()) as connection, connection:
        return connection.execute("SELECT COUNT(*) FROM loans WHERE returned_on IS NULL").fetchone()[0]


def get_loans(active_only=False):
    """Return loan records, including their associated book title."""
    query = """
        SELECT loans.loan_id, books.book_title, loans.borrower_name, loans.borrowed_on,
               loans.due_date, loans.returned_on
        FROM loans JOIN books ON books.book_id = loans.book_id
    """
    if active_only:
        query += " WHERE loans.returned_on IS NULL"
    query += " ORDER BY loans.returned_on IS NULL DESC, loans.due_date, loans.loan_id DESC"
    with closing(get_connection()) as connection, connection:
        rows = connection.execute(query).fetchall()
    return [dict(row) for row in rows]


def borrow_book(book_id, borrower_name, due_date, borrowed_on):
    """Record one loan and reduce the available copy count atomically."""
    borrower = borrower_name.strip()
    if not borrower:
        raise ValueError("Enter the borrower's name.")
    if due_date < borrowed_on:
        raise ValueError("The due date cannot be before the borrowing date.")
    with closing(get_connection()) as connection, connection:
        book = connection.execute(
            "SELECT available_copies FROM books WHERE book_id = ?", (book_id,)
        ).fetchone()
        if book is None:
            raise ValueError("That book could not be found.")
        if book["available_copies"] < 1:
            raise ValueError("No copies of this book are currently available.")
        connection.execute(
            "UPDATE books SET available_copies = available_copies - 1 WHERE book_id = ?", (book_id,)
        )
        connection.execute(
            "INSERT INTO loans (book_id, borrower_name, borrowed_on, due_date) VALUES (?, ?, ?, ?)",
            (book_id, borrower, borrowed_on, due_date),
        )


def return_book(loan_id, returned_on):
    """Close an active loan and add the returned copy back to inventory."""
    with closing(get_connection()) as connection, connection:
        loan = connection.execute(
            "SELECT book_id, returned_on FROM loans WHERE loan_id = ?", (loan_id,)
        ).fetchone()
        if loan is None or loan["returned_on"] is not None:
            raise ValueError("That active loan could not be found.")
        connection.execute("UPDATE loans SET returned_on = ? WHERE loan_id = ?", (returned_on, loan_id))
        connection.execute(
            "UPDATE books SET available_copies = available_copies + 1 WHERE book_id = ?",
            (loan["book_id"],),
        )
