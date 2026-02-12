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


@app.route('/addentry', methods=['POST'])
def add_entry():
    """Accept a single entry object and insert it into the database.

    Expected JSON format:
    - An object with entry fields: {...}

    The entry object may include the fields:
      - entry_date (YYYY-MM-DD) [required]
      - start_time (HH:MM or HH:MM:SS) [required]
      - duration_minutes (int) [required]
      - description (string)
      - notes (string)
      - category_id (int) - the category ID
      - billable (0|1)
      - project_id (int) - the project ID
      - company_id (int) - the company ID

    Returns JSON: {"inserted": 1} or error message.
    """
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    if not isinstance(payload, dict):
        return jsonify({"error": "Expected a JSON object"}), 400

    entry_date = payload.get('entry_date')
    start_time = payload.get('start_time')
    duration = payload.get('duration_minutes')
    if entry_date is None or start_time is None or duration is None:
        return jsonify({"error": "Missing required fields: 'entry_date', 'start_time', 'duration_minutes'"}), 400

    description = payload.get('description')
    notes = payload.get('notes')
    category_id = payload.get('category_id')
    billable = int(payload.get('billable', 0) or 0)
    project_id = payload.get('project_id')
    company_id = payload.get('company_id')

    try:
        duration_minutes = int(duration)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid duration_minutes"}), 400

    entry = {
        'entry_date': entry_date,
        'start_time': start_time,
        'duration_minutes': duration_minutes,
        'description': description,
        'notes': notes,
        'category_id': category_id,
        'billable': billable,
        'project_id': project_id,
        'company_id': company_id
    }
    
    try:
        timesheet_db.insert_entry(entry)
        return jsonify({"inserted": 1})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/getentries', methods=['GET'])
def get_entries():
    """Return entries between `start` and `end` (inclusive).

    Query params: 
      - `start` and `end` in YYYY-MM-DD format [required]
      - `period` set to 'current_month' as a shortcut for the current month
      - `company_id` (optional integer)
      - `category_id` (optional integer)
      - `project_id` (optional integer)
    """
    start = request.args.get('start')
    end = request.args.get('end')

    # Allow a shortcut to request the current calendar month
    # Usage: /getentries?period=current_month
    if not start or not end:
        period = request.args.get('period')
        if period == 'current_month':
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

    # Get optional filter IDs
    company_id = request.args.get('company_id', type=int)
    category_id = request.args.get('category_id', type=int)
    project_id = request.args.get('project_id', type=int)
    
    try:
        rows = timesheet_db.get_report_between(start, end, company_id=company_id, category_id=category_id, project_id=project_id)
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