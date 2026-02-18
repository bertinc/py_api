# Py API - Timesheet Utility

Small Python project providing a simple timesheet utility with a lightweight SQLite backend.

**Status:** Minimal Flask API + DB init script — ready to inspect and run.

## Features

- Persist time entries in a local SQLite database using `init_timesheet_db.sql`.
- A small Flask API exposing endpoints in `timesheet.py`.
- `db.py` implements database operations; `constants.py` holds configuration.

## Requirements

- Python 3.10 or newer.
- Runtime dependencies are listed in `requirements.txt` (Flask, Flask-Cors).

## Quickstart

1) Create and activate a virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install runtime dependencies:

```powershell
pip install -r requirements.txt
```

3) Initialize the SQLite database (creates schema):

Note: `timesheet.py` calls `TimesheetDB().init_db()` at startup and will create `timesheet.db` automatically if it does not exist. The explicit steps below are optional — useful if you want to pre-create, inspect, or modify the schema before starting the server.

```powershell
# If you have the sqlite3 CLI installed
sqlite3 timesheet.db < init_timesheet_db.sql

# Or from Python (Windows-friendly alternative)
```powershell
python -c "import sqlite3, pathlib; sql=pathlib.Path('init_timesheet_db.sql').read_text(); conn=sqlite3.connect('timesheet.db'); conn.executescript(sql); conn.close()"
```
```

4) Start the API server:

```powershell
python timesheet.py
```

The server listens on port `8001` by default (host `0.0.0.0` in `timesheet.py`).

Run with the CLI wrapper
------------------------

A small CLI wrapper `cli.py` is included to run the server with configurable host and port.


Examples (after activating your virtualenv and installing requirements):

```powershell
# bind to localhost on port 5000
python cli.py --host 127.0.0.1 --port 5000

# bind to all interfaces on port 8001 with debug and reloader enabled
python cli.py --host 0.0.0.0 --port 8001 --debug --reload

# show help
python cli.py --help
```

Notes:
- `--debug` enables Flask debug mode. `--reload` toggles the Werkzeug reloader independently.
- `cli.py` validates the port range and logs a concise startup message by default.


## Example API Usage

Replace `localhost:8001` with your host/port if different.

- Add a timesheet entry (POST `/addentry`):

```bash
curl -X POST http://localhost:8001/addentry \
	-H "Content-Type: application/json" \
	-d '{"entry_date":"2026-02-13","start_time":"09:00","duration_minutes":60,"description":"Dev work","notes":"API improvements","billable":1}'
```

- Get entries between two dates (GET `/getentries`):

```bash
curl "http://localhost:8001/getentries?start=2026-02-01&end=2026-02-28"
```

- Get all categories (GET `/categories`):

```bash
curl "http://localhost:8001/categories"
```

- Add a category (POST `/categories`):

```bash
curl -X POST http://localhost:8001/categories \
	-H "Content-Type: application/json" \
	-d '{"code":"DEV","description":"Development work"}'
```

- Calculate total hours and pay for a company (GET `/gethoursandpay`):

```bash
curl "http://localhost:8001/gethoursandpay?start=2026-02-01&end=2026-02-28&company_id=1"
```

### Update endpoints (examples)

- Update an entry (POST `/updateentry`):

```bash
curl -X POST http://localhost:8001/updateentry \
	-H "Content-Type: application/json" \
	-d '{"id":5,"duration_minutes":90,"description":"Updated work"}'
```

- Update a company (PUT `/companies`):

```bash
curl -X PUT http://localhost:8001/companies \
	-H "Content-Type: application/json" \
	-d '{"company_id":2,"description":"New description","pay_rate":85.5}'
```

- Update a category (PUT `/categories`):

```bash
curl -X PUT http://localhost:8001/categories \
	-H "Content-Type: application/json" \
	-d '{"category_id":4,"code":"DEV","description":"Development work"}'
```

- Update a project (PUT `/projects`):

```bash
curl -X PUT http://localhost:8001/projects \
	-H "Content-Type: application/json" \
	-d '{"project_id":7,"name":"New project name","due_date":"2026-03-20"}'
```

### C# example

See `UpdateExamples.cs` for a simple C# console program that calls all four update endpoints. Build and run with the .NET SDK:

```powershell
dotnet new console -n UpdateExamplesApp -o UpdateExamplesApp
copy UpdateExamples.cs UpdateExamplesApp\Program.cs
cd UpdateExamplesApp
dotnet run
```

## Notes & Troubleshooting

- `timesheet.py` imports `flask` and `flask_cors`. Ensure you installed `requirements.txt`.
- CORS is enabled in the app via `CORS(app)`; browser-side issues generally stem from using the wrong origin or port.
- The DB file `timesheet.db` must exist in the working directory unless you change the path in `constants.py`.

## Files Quick Reference

- `constants.py` — configuration (DB path, date format).
- `db.py` — database helpers and operations (`TimesheetDB`).
- `timesheet.py` — Flask-based API server and endpoints.
- `init_timesheet_db.sql` — SQL schema for initial DB setup.
- `requirements.txt` — runtime requirements: `Flask` and `Flask-Cors`.

**Running tests**

- **Install test deps:**

```powershell
pip install -r requirements.txt
```

- **Run all tests (pytest):**

```powershell
pytest -q
```

- **Run a single test file:**

```powershell
pytest tests/test_db.py -q
```

Notes:
- Tests use a temporary database file by default. You can also configure
	`TimesheetDB` to use an in-memory or shared-memory SQLite database for
	faster isolation in CI.

