"""A beginner-friendly library inventory and borrowing app."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from database import (
    add_book,
    borrow_book,
    delete_book,
    get_active_loan_count,
    get_books,
    get_category_summary,
    get_loans,
    get_most_available_book,
    get_total_copies,
    initialize_database,
    return_book,
    update_book,
)


st.set_page_config(page_title="ABC College Library", page_icon="📚", layout="wide")
initialize_database()

st.title("📚 ABC Engineering College Library")
st.caption("Manage the collection, keep an eye on low stock, and track borrowed books.")

books = get_books()
total_titles = len(books)
total_copies = get_total_copies()
most_stocked = get_most_available_book()
low_stock_count = sum(book["available_copies"] <= 2 for book in books)
active_loan_count = get_active_loan_count()

metrics = st.columns(5)
metrics[0].metric("Book titles", total_titles)
metrics[1].metric("Available copies", total_copies)
metrics[2].metric("Low stock (≤2)", low_stock_count)
metrics[3].metric("Books on loan", active_loan_count)
metrics[4].metric("Most stocked", most_stocked["book_title"] if most_stocked else "—", f'{most_stocked["available_copies"]} copies' if most_stocked else None)

add_tab, view_tab, manage_tab, loans_tab, summary_tab = st.tabs(
    ["➕ Add a book", "📖 View books", "🛠️ Edit or remove", "🔄 Borrow & return", "📊 Category summary"]
)

categories = ["Programming", "Artificial Intelligence", "Data Science", "Mathematics", "Electronics", "Management", "Other"]

with add_tab:
    st.subheader("Add a book to the library")
    with st.form("add_book_form", clear_on_submit=True):
        title = st.text_input("Book title", placeholder="e.g. Introduction to Python")
        author = st.text_input("Author name", placeholder="e.g. A. Student")
        category = st.selectbox("Category", categories)
        copies = st.number_input("Available copies", min_value=1, max_value=100000, value=1, step=1)
        submitted = st.form_submit_button("Add book", type="primary", use_container_width=True)
        if submitted:
            if not title.strip() or not author.strip():
                st.error("Enter both the book title and author name.")
            else:
                try:
                    add_book(title, author, category, int(copies))
                    st.success(f'“{title.strip()}” was added to the library.')
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

with view_tab:
    st.subheader("Books in the library")
    if books:
        filter_col, search_col = st.columns([1, 2])
        category_filter = filter_col.selectbox("Filter by category", ["All categories"] + sorted({book["category"] for book in books}))
        search = search_col.text_input("Search title or author", placeholder="Start typing to filter…")
        shown = [
            book for book in books
            if (category_filter == "All categories" or book["category"] == category_filter)
            and search.casefold() in f'{book["book_title"]} {book["author_name"]}'.casefold()
        ]
        display_rows = []
        for book in shown:
            row = dict(book)
            row["Stock status"] = "🔴 Low stock" if book["available_copies"] <= 2 else "🟢 In stock"
            display_rows.append(row)
        st.caption(f"Showing {len(shown)} of {len(books)} titles. Low stock means two or fewer available copies.")
        st.dataframe(
            pd.DataFrame(display_rows).rename(columns={"book_id": "ID", "book_title": "Book title", "author_name": "Author", "category": "Category", "available_copies": "Available copies"}),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No books yet. Use the Add a book tab to enter your first title.")

with manage_tab:
    st.subheader("Edit book details")
    if books:
        book_labels = {f'{book["book_title"]} — {book["author_name"]} (ID {book["book_id"]})': book for book in books}
        selected_label = st.selectbox("Choose a book to edit", list(book_labels), key="edit_book_select")
        selected_book = book_labels[selected_label]
        with st.form("edit_book_form"):
            edit_title = st.text_input("Book title", value=selected_book["book_title"])
            edit_author = st.text_input("Author name", value=selected_book["author_name"])
            category_options = categories.copy()
            if selected_book["category"] not in category_options:
                category_options.append(selected_book["category"])
            edit_category = st.selectbox("Category", category_options, index=category_options.index(selected_book["category"]))
            edit_copies = st.number_input("Available copies", min_value=0, max_value=100000, value=selected_book["available_copies"], step=1)
            save_edit = st.form_submit_button("Save changes", type="primary")
            if save_edit:
                try:
                    update_book(selected_book["book_id"], edit_title, edit_author, edit_category, int(edit_copies))
                    st.success("Book details updated.")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

        st.divider()
        st.subheader("Remove a book")
        st.caption("Books with borrowing history are protected from deletion so loan records are preserved.")
        confirm_delete = st.checkbox(f'I understand that “{selected_book["book_title"]}” will be removed permanently.', key="confirm_delete")
        if st.button("Remove selected book", disabled=not confirm_delete, type="secondary"):
            try:
                delete_book(selected_book["book_id"])
                st.success("Book removed.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    else:
        st.info("Add a book first to edit or remove it.")

with loans_tab:
    st.subheader("Record a borrowed book")
    available_books = [book for book in books if book["available_copies"] > 0]
    if available_books:
        loan_labels = {f'{book["book_title"]} — {book["available_copies"]} available (ID {book["book_id"]})': book for book in available_books}
        with st.form("borrow_form", clear_on_submit=True):
            selected_loan_label = st.selectbox("Book", list(loan_labels))
            borrower = st.text_input("Borrower's name")
            borrow_date = st.date_input("Borrowed on", value=date.today())
            due_date = st.date_input("Due date", value=date.today() + timedelta(days=14), min_value=date.today())
            record_loan = st.form_submit_button("Record borrowing", type="primary")
            if record_loan:
                try:
                    borrow_book(loan_labels[selected_loan_label]["book_id"], borrower, due_date.isoformat(), borrow_date.isoformat())
                    st.success("Borrowing recorded; available copies updated.")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    else:
        st.info("There are no available copies to borrow right now.")

    st.divider()
    st.subheader("Active loans and returns")
    active_loans = get_loans(active_only=True)
    if active_loans:
        loan_options = {
            f'#{loan["loan_id"]} · {loan["book_title"]} · {loan["borrower_name"]} · due {loan["due_date"]}': loan
            for loan in active_loans
        }
        return_label = st.selectbox("Choose a loan to return", list(loan_options))
        if st.button("Mark as returned", type="primary"):
            try:
                return_book(loan_options[return_label]["loan_id"], date.today().isoformat())
                st.success("Return recorded; one copy was added back to available stock.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    else:
        st.info("There are no active loans.")

    loan_history = get_loans()
    if loan_history:
        today = date.today().isoformat()
        for loan in loan_history:
            if loan["returned_on"]:
                loan["Status"] = f'Returned {loan["returned_on"]}'
            elif loan["due_date"] < today:
                loan["Status"] = "🔴 Overdue"
            else:
                loan["Status"] = "🟡 Borrowed"
        st.subheader("Borrowing history")
        st.dataframe(pd.DataFrame(loan_history).rename(columns={"loan_id": "Loan ID", "book_title": "Book", "borrower_name": "Borrower", "borrowed_on": "Borrowed on", "due_date": "Due date", "returned_on": "Returned on"}), use_container_width=True, hide_index=True)

with summary_tab:
    st.subheader("Inventory by category")
    summary = get_category_summary()
    if summary:
        st.dataframe(pd.DataFrame(summary).rename(columns={"category": "Category", "title_count": "Book titles", "total_copies": "Available copies"}), use_container_width=True, hide_index=True)
        st.bar_chart(pd.DataFrame(summary).set_index("category")["total_copies"], y_label="Available copies")
    else:
        st.info("Category totals will appear after books are added.")

st.divider()
st.caption("Records are stored locally in library.db. Back up that file to keep a copy of your inventory.")
