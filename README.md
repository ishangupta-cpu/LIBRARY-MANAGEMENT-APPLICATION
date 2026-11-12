# ABC Engineering College Library Management System

A beginner-friendly inventory app built with Python, Streamlit, and SQLite. Staff can add, edit, and remove books; search and filter the inventory; see low-stock reminders and category totals; and record borrowing and returns. Borrowing reduces available stock and returning restores it. Books with borrowing history are protected from deletion so the history remains intact.

## Requirements

- Python 3.10 or newer
- Git
- Internet access for the first dependency installation

## Setup in VS Code (Windows PowerShell)

Open this folder in VS Code, then open **Terminal → New Terminal** and run:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. This only changes policy for the current terminal window.

## Run the app

```powershell
streamlit run app.py
```

Streamlit opens the app in your browser. On first launch, the app creates `library.db` and the `books` table automatically in this project folder. The database file is intentionally excluded from Git; keep a backup if its records matter.

## Run the automated checks

```powershell
python -m unittest -v
```

The checks use a temporary database and do not change your library records.

## Git commands

```powershell
git init
git add .
git commit -m "Build library management system"
```

After making changes, use `git status`, `git add <file>`, and `git commit -m "Describe your change"` to save a checkpoint.

## Project files

- `app.py` — Streamlit screens and form validation
- `database.py` — SQLite schema, inserts, and summary queries
- `test_database.py` — automated checks for storage, statistics, edits, and borrowing/returns
- `prompts_used.md` — prompts used while building the project
- `requirements.txt` — Python packages to install
