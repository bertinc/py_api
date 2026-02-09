import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS
from db import TimesheetDB as DB
import constants as const
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app) # enable CORS for all routes and origins

# initialize DB once at startup
timesheet_db = DB()
timesheet_db.init_db()

# TypeError: Failed to fetch
# To deal with CORS
# On server: pip install Flask-CORS
# In code: import CORS, enable all routes and origins

@app.route('/addrow')
def addrow():
    return "Row added!"


@app.route('/addentries', methods=['POST'])
def add_entries():
    """Accept a JSON array of entry objects and insert them in bulk.

    Expected JSON formats:
    - An array of objects: [{...}, {...}]
    - Or an object with `entries` key: {"entries": [{...}, ...]}

    Each entry object may include the fields:
      - entry_date (YYYY-MM-DD) [required]
      - start_time (HH:MM or HH:MM:SS) [required]
      - duration_minutes (int) [required]
      - description (string)
      - notes (string)
      - category_code (string)
      - billable (0|1)
      - project_code (string)
      - company_key (string)  -- company name used as lookup key

    Returns JSON: {"inserted": <n>} or error message.
    """
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    entries_src = payload.get('entries') if isinstance(payload, dict) and 'entries' in payload else payload
    if not isinstance(entries_src, list):
        return jsonify({"error": "Expected a JSON array of entries or an object with 'entries' list"}), 400

    prepared = []
    for idx, item in enumerate(entries_src):
        if not isinstance(item, dict):
            return jsonify({"error": f"Each entry must be an object (index {idx})"}), 400

        entry_date = item.get('entry_date')
        start_time = item.get('start_time')
        duration = item.get('duration_minutes')
        if entry_date is None or start_time is None or duration is None:
            return jsonify({"error": f"Missing required fields on entry index {idx}: 'entry_date', 'start_time', 'duration_minutes'"}), 400

        description = item.get('description')
        notes = item.get('notes')
        category_code = item.get('category_code')
        billable = int(item.get('billable', 0) or 0)
        project_code = item.get('project_code')
        company_key = item.get('company_key')

        try:
            duration_minutes = int(duration)
        except (TypeError, ValueError):
            return jsonify({"error": f"Invalid duration_minutes at index {idx}"}), 400

        prepared.append((entry_date, start_time, duration_minutes, description, notes, category_code, billable, project_code, company_key))

    try:
        timesheet_db.insert_bulk_entries(prepared)
        return jsonify({"inserted": len(prepared)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/getentries', methods=['GET'])
def get_entries():
    """Return entries between `start` and `end` (inclusive).

    Query params: `start` and `end` in YYYY-MM-DD format.
    """
    start = request.args.get('start')
    end = request.args.get('end')

    # Allow a shortcut to request the current calendar month
    # Usage: /getentries?current_month=1  or /getentries?period=current_month
    if not start or not end:
        period = request.args.get('period')
        current_flag = request.args.get('current_month')
        if (current_flag and str(current_flag).lower() in ('1', 'true', 'yes', 'on')) or (period == 'current_month'):
            now = datetime.now()
            # first day of current month
            start = now.replace(day=1).strftime(const.DATE_FORMAT)
            # compute last day of month: go to first of next month then subtract one day
            first_next = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
            last_day = first_next - timedelta(days=1)
            end = last_day.strftime(const.DATE_FORMAT)
        else:
            return jsonify({"error": "Missing 'start' or 'end' query parameter"}), 400

    # validate format
    try:
        datetime.strptime(start, const.DATE_FORMAT)
        datetime.strptime(end, const.DATE_FORMAT)
    except Exception:
        return jsonify({"error": "Dates must be in YYYY-MM-DD format"}), 400

    company = request.args.get('company')
    category = request.args.get('category')
    project = request.args.get('project')
    try:
        rows = timesheet_db.get_report_between(start, end, company=company, category=category, project=project)
        keys = [
            'id', 'entry_date', 'start_time', 'duration_minutes', 'end_time',
            'description', 'notes', 'category_code', 'category_description',
            'project_code', 'project_name', 'company_name', 'billable',
            'created_at', 'updated_at'
        ]
        entries = [dict(zip(keys, row)) for row in rows]
        return jsonify({"count": len(entries), "entries": entries})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/categories', methods=['GET'])
def get_categories():
    """Return all categories from the database."""
    try:
        cats = timesheet_db.get_categories()
        return jsonify({"count": len(cats), "categories": cats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/companies', methods=['GET'])
def get_companies():
    """Return all companies from the database."""
    try:
        companies = timesheet_db.get_companies()
        return jsonify({"count": len(companies), "companies": companies})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/projects', methods=['GET'])
def get_projects():
    """Return projects. Use optional `company` query param to filter by company name."""
    try:
        company = request.args.get('company')
        projects = timesheet_db.get_projects(company=company)
        return jsonify({"count": len(projects), "projects": projects})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# To access this api remotely on the nextwork
# you must include the host as 0.0.0.0. This
# allows flask to listen on more than just localhost.
if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port=8001)