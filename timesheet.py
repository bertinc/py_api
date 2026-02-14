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
            'description', 'notes', 'category_id', 'category_code', 'category_description',
            'project_id', 'project_code', 'project_name', 'company_id', 'company_name',
            'billable', 'created_at', 'updated_at'
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


@app.route('/categories', methods=['POST'])
def add_category():
    """Add a new category via the same `/categories` endpoint (POST).

    Expected JSON:
      - code (string) [required]
      - description (string)

    Returns JSON: {"inserted": 1, "id": <new_id>} or error.
    """
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    code = payload.get('code')
    if not code:
        return jsonify({"error": "Missing required field: 'code'"}), 400

    description = payload.get('description')

    try:
        new_id = timesheet_db.add_category(code=code, description=description)
        if new_id:
            return jsonify({"inserted": 1, "id": new_id})
        else:
            return jsonify({"error": "Could not add category (maybe duplicate code)"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/categories', methods=['DELETE'])
def remove_category():
    """Remove a category via the same `/categories` endpoint (DELETE).

    Expected JSON:
      - {"category_id": <int>}

    Returns JSON: {"deleted": 1} or error.
    """
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    category_id = payload.get('category_id')
    if category_id is None:
        return jsonify({"error": "Provide 'category_id' to remove a category"}), 400

    try:
        try:
            category_id = int(category_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid 'category_id'"}), 400

        success = timesheet_db.remove_category(category_id=category_id)
        if success:
            return jsonify({"deleted": 1})
        else:
            return jsonify({"error": "Category not found or could not be deleted (may have dependent entries)"}), 404
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


@app.route('/companies', methods=['POST'])
def add_company():
    """Add a new company via the same `/companies` endpoint (POST).

    Expected JSON:
      - name (string) [required]
      - description (string)
      - pay_rate (number)

    Returns JSON: {"inserted": 1, "id": <new_id>} or error.
    """
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    name = payload.get('name')
    if not name:
        return jsonify({"error": "Missing required field: 'name'"}), 400

    description = payload.get('description')
    pay_rate = payload.get('pay_rate')
    if pay_rate is not None:
        try:
            pay_rate = float(pay_rate)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid 'pay_rate' value"}), 400

    try:
        new_id = timesheet_db.add_company(name=name, description=description, pay_rate=pay_rate or 0.0)
        if new_id:
            return jsonify({"inserted": 1, "id": new_id})
        else:
            return jsonify({"error": "Could not add company (maybe duplicate name)"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/companies', methods=['DELETE'])
def remove_company():
    """Remove a company via the same `/companies` endpoint (DELETE).

    Expected JSON:
      - {"company_id": <int>}

    Returns JSON: {"deleted": 1} or error.
    """
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    company_id = payload.get('company_id')
    if company_id is None:
        return jsonify({"error": "Provide 'company_id' to remove a company"}), 400

    try:
        try:
            company_id = int(company_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid 'company_id'"}), 400

        success = timesheet_db.remove_company(company_id=company_id)
        if success:
            return jsonify({"deleted": 1})
        else:
            return jsonify({"error": "Company not found or could not be deleted (may have dependent entries)"}), 404
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


@app.route('/projects', methods=['POST'])
def add_project():
    """Add a new project using the same `/projects` endpoint (POST).

    Expected JSON:
      - code (string) [required]
      - name (string)
      - due_date (YYYY-MM-DD)
      - company_id (int)
      - description (string)

    Returns JSON: {"inserted": 1, "id": <new_id>} or error.
    """
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    code = payload.get('code')
    if not code:
        return jsonify({"error": "Missing required field: 'code'"}), 400

    name = payload.get('name')
    due_date = payload.get('due_date')
    company_id = payload.get('company_id')
    description = payload.get('description')

    if due_date:
        try:
            datetime.strptime(due_date, const.DATE_FORMAT)
        except Exception:
            return jsonify({"error": "Invalid due_date format. Use YYYY-MM-DD"}), 400

    try:
        new_id = timesheet_db.add_project(code=code, name=name, due_date=due_date, company_id=company_id, description=description)
        if new_id:
            return jsonify({"inserted": 1, "id": new_id})
        else:
            return jsonify({"error": "Could not add project (maybe duplicate code)"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/projects', methods=['DELETE'])
def remove_project():
    """Remove a project using the same `/projects` endpoint (DELETE).

    Expected JSON:
      - {"project_id": <int>}

    Returns JSON: {"deleted": 1} or error.
    """
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    project_id = payload.get('project_id')
    if project_id is None:
        return jsonify({"error": "Provide 'project_id' to remove a project"}), 400

    try:
        try:
            project_id = int(project_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid 'project_id'"}), 400

        success = timesheet_db.remove_project(project_id=project_id)
        if success:
            return jsonify({"deleted": 1})
        else:
            return jsonify({"error": "Project not found or could not be deleted (may have dependent entries)"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/updateentry', methods=['POST'])
def update_entry():
    """Update an entry by id or by entry_date + start_time.

    Expected JSON:
      - Either `id` (int) OR both `entry_date` (YYYY-MM-DD) and `start_time` (HH:MM...)
      - Fields to update: entry_date, start_time, duration_minutes, description, notes,
        category_id, billable, project_id, company_id
    """
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    entry_id = payload.get('id')
    entry_date = payload.get('entry_date')
    start_time = payload.get('start_time')

    update_fields = {}
    for key in ('entry_date', 'start_time', 'duration_minutes', 'description', 'notes', 'category_id', 'billable', 'project_id', 'company_id'):
        if key in payload:
            update_fields[key] = payload.get(key)

    if 'duration_minutes' in update_fields:
        try:
            update_fields['duration_minutes'] = int(update_fields['duration_minutes'])
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid 'duration_minutes'"}), 400

    if 'billable' in update_fields:
        try:
            update_fields['billable'] = int(update_fields['billable'] or 0)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid 'billable' value"}), 400

    for fk in ('category_id', 'project_id', 'company_id'):
        if fk in update_fields and update_fields[fk] is not None:
            try:
                update_fields[fk] = int(update_fields[fk])
            except (TypeError, ValueError):
                return jsonify({"error": f"Invalid '{fk}'"}), 400

    if entry_id is None and not (entry_date and start_time):
        return jsonify({"error": "Provide 'id' or both 'entry_date' and 'start_time' to identify the entry"}), 400

    if entry_date:
        try:
            datetime.strptime(entry_date, const.DATE_FORMAT)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid entry_date format. Use YYYY-MM-DD"}), 400

    try:
        if entry_id is not None:
            try:
                entry_id = int(entry_id)
            except (TypeError, ValueError):
                return jsonify({"error": "Invalid 'id'"}), 400
            success = timesheet_db.update_entry(entry_id=entry_id, update_fields=update_fields)
        else:
            success = timesheet_db.update_entry(entry_date=entry_date, start_time=start_time, update_fields=update_fields)

        if success:
            return jsonify({"updated": 1})
        else:
            return jsonify({"error": "Entry not found or not updated"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/companies', methods=['PUT'])
def update_company():
    """Update a company. Identify by `company_id` or `name`.

    Expected JSON:
      - `company_id` (int) OR `name` (string)
      - Fields: name, description, pay_rate
    """
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    company_id = payload.get('company_id')
    name = payload.get('name') if 'name' in payload else None

    update_fields = {}
    if 'name' in payload:
        update_fields['name'] = payload.get('name')
    if 'description' in payload:
        update_fields['description'] = payload.get('description')
    if 'pay_rate' in payload:
        try:
            update_fields['pay_rate'] = float(payload.get('pay_rate'))
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid 'pay_rate'"}), 400

    if not update_fields:
        return jsonify({"error": "No fields to update provided"}), 400

    try:
        if company_id is not None:
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                return jsonify({"error": "Invalid 'company_id'"}), 400
            success = timesheet_db.update_company(company_id=company_id, update_fields=update_fields)
        elif name is not None and ('description' in update_fields or 'pay_rate' in update_fields or ('name' in update_fields and update_fields['name'] != name)):
            # allow updating by name; if changing name, the payload contains both old and new names
            success = timesheet_db.update_company(name=name, update_fields=update_fields)
        else:
            return jsonify({"error": "Provide 'company_id' or 'name' to identify the company"}), 400

        if success:
            return jsonify({"updated": 1})
        else:
            return jsonify({"error": "Company not found or not updated"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/categories', methods=['PUT'])
def update_category():
    """Update a category. Identify by `category_id` or `code`.

    Expected JSON:
      - `category_id` (int) OR `code` (string)
      - Fields: code, description
    """
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    category_id = payload.get('category_id')
    code = payload.get('code') if 'code' in payload else None

    update_fields = {}
    if 'code' in payload:
        update_fields['code'] = payload.get('code')
    if 'description' in payload:
        update_fields['description'] = payload.get('description')

    if not update_fields:
        return jsonify({"error": "No fields to update provided"}), 400

    try:
        if category_id is not None:
            try:
                category_id = int(category_id)
            except (TypeError, ValueError):
                return jsonify({"error": "Invalid 'category_id'"}), 400
            success = timesheet_db.update_category(category_id=category_id, update_fields=update_fields)
        elif code is not None:
            # update by code
            success = timesheet_db.update_category(code=code, update_fields=update_fields)
        else:
            return jsonify({"error": "Provide 'category_id' or 'code' to identify the category"}), 400

        if success:
            return jsonify({"updated": 1})
        else:
            return jsonify({"error": "Category not found or not updated"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/projects', methods=['PUT'])
def update_project():
    """Update a project. Identify by `project_id` or `code`.

    Expected JSON:
      - `project_id` (int) OR `code` (string)
      - Fields: code, name, due_date (YYYY-MM-DD), company_id, description
    """
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    project_id = payload.get('project_id')
    code = payload.get('code') if 'code' in payload else None

    update_fields = {}
    for key in ('code', 'name', 'due_date', 'company_id', 'description'):
        if key in payload:
            update_fields[key] = payload.get(key)

    if 'due_date' in update_fields and update_fields['due_date']:
        try:
            datetime.strptime(update_fields['due_date'], const.DATE_FORMAT)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid due_date format. Use YYYY-MM-DD"}), 400

    if 'company_id' in update_fields and update_fields['company_id'] is not None:
        try:
            update_fields['company_id'] = int(update_fields['company_id'])
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid 'company_id'"}), 400

    if not update_fields:
        return jsonify({"error": "No fields to update provided"}), 400

    try:
        if project_id is not None:
            try:
                project_id = int(project_id)
            except (TypeError, ValueError):
                return jsonify({"error": "Invalid 'project_id'"}), 400
            success = timesheet_db.update_project(project_id=project_id, update_fields=update_fields)
        elif code is not None:
            success = timesheet_db.update_project(code=code, update_fields=update_fields)
        else:
            return jsonify({"error": "Provide 'project_id' or 'code' to identify the project"}), 400

        if success:
            return jsonify({"updated": 1})
        else:
            return jsonify({"error": "Project not found or not updated"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/removeentry', methods=['POST'])
def remove_entry():
    """Delete a timesheet entry by ID or by entry_date and start_time.

    Expected JSON format - one of the following:
    - {"id": <int>} to delete by entry ID
    - {"entry_date": "YYYY-MM-DD", "start_time": "HH:MM"} to delete by date and time

    Returns JSON: {"deleted": 1} on success or error message.
    """
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    if not isinstance(payload, dict):
        return jsonify({"error": "Expected a JSON object"}), 400

    entry_id = payload.get('id')
    entry_date = payload.get('entry_date')
    start_time = payload.get('start_time')

    # Check if we have either ID or both entry_date and start_time
    if entry_id is not None:
        # Delete by ID
        try:
            entry_id = int(entry_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid entry ID"}), 400
        
        try:
            success = timesheet_db.delete_entry(entry_id=entry_id)
            if success:
                return jsonify({"deleted": 1})
            else:
                return jsonify({"error": "Entry not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    elif entry_date is not None and start_time is not None:
        # Delete by entry_date and start_time
        try:
            datetime.strptime(entry_date, const.DATE_FORMAT)
        except (ValueError, AttributeError):
            return jsonify({"error": "Invalid entry_date format. Use YYYY-MM-DD"}), 400
        
        try:
            success = timesheet_db.delete_entry(entry_date=entry_date, start_time=start_time)
            if success:
                return jsonify({"deleted": 1})
            else:
                return jsonify({"error": "Entry not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    else:
        return jsonify({"error": "Must provide either 'id' or both 'entry_date' and 'start_time'"}), 400


@app.route('/gethoursandpay', methods=['GET'])
def get_hours_and_pay():
    """Return total hours and pay for a company between `start` and `end`.

    Query params:
      - `start` and `end` in YYYY-MM-DD format [required] or use `period=current_month`
      - `company_id` (required integer)
      - `category_id` (optional integer)
      - `project_id` (optional integer)
    """
    start = request.args.get('start')
    end = request.args.get('end')

    if not start or not end:
        period = request.args.get('period')
        if period == 'current_month':
            now = datetime.now()
            start = now.replace(day=1).strftime(const.DATE_FORMAT)
            first_next = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
            last_day = first_next - timedelta(days=1)
            end = last_day.strftime(const.DATE_FORMAT)
        else:
            return jsonify({"error": "Missing 'start' or 'end' query parameter"}), 400

    try:
        datetime.strptime(start, const.DATE_FORMAT)
        datetime.strptime(end, const.DATE_FORMAT)
    except Exception:
        return jsonify({"error": "Dates must be in YYYY-MM-DD format"}), 400

    company_id = request.args.get('company_id', type=int)
    if company_id is None:
        return jsonify({"error": "Missing 'company_id' query parameter"}), 400

    category_id = request.args.get('category_id', type=int)
    project_id = request.args.get('project_id', type=int)

    try:
        result = timesheet_db.get_hours_and_pay(start, end, company_id, category_id=category_id, project_id=project_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# To access this api remotely on the nextwork
# you must include the host as 0.0.0.0. This
# allows flask to listen on more than just localhost.
if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port=8001)