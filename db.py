"""To make doing database operations easier"""
import sqlite3
import os
from typing import Optional

import constants as const

class TimesheetDB:
    """
    Does all the needed database interactions.
    """
    def __init__(self, db_file: Optional[str] = None, sql_file: Optional[str] = None) -> None:
        """
        Initialize TimesheetDB.

        Backwards compatible: when no arguments are provided this uses the
        constants defined in `constants.py`. For testing you can pass a
        specific `db_file` (e.g. ':memory:' or a path inside a tmpdir) and an
        explicit `sql_file` path to initialize the schema.

        Args:
            db_file (str|None): Path to the SQLite database file or
                ':memory:' for an in-memory DB. If None, uses the default
                location from `constants.py`.
            sql_file (str|None): Path to the SQL init script. If None, uses
                the default from `constants.py`.
        """
        # Keep signature backwards-compatible by providing defaults via const
        self.file_path = const.PATH
        self.db_file = os.sep.join([self.file_path, const.DB_FILENAME])
        self.sql_file = os.sep.join([self.file_path, const.SQL_INIT_FILE])
        # If overrides provided, use them; otherwise fall back to constants
        if db_file:
            self.db_file = db_file
        if sql_file:
            self.sql_file = sql_file
        # Allow overriding after construction if desired (kept for compatibility)
        self.conn = None

    def close_connection(self):
        """
        Close the active SQLite connection if one exists.

        This safely closes `self.conn` and leaves it ready for the next
        `open_connection()` call.
        """
        if self.conn:
            self.conn.close()

    def open_connection(self):
        """
        Open and return a sqlite3 connection to the configured database file.

        The connection will have SQLite foreign key enforcement enabled via
        `PRAGMA foreign_keys = ON` when supported by the underlying SQLite
        build. The opened connection is stored on `self.conn` and also
        returned to the caller.

        Returns:
            sqlite3.Connection: an open SQLite connection object.
        """
        # Support SQLite URI filenames (e.g. file:memdb1?mode=memory&cache=shared)
        use_uri = isinstance(self.db_file, str) and self.db_file.startswith("file:")
        if use_uri:
            self.conn = sqlite3.connect(self.db_file, uri=True)
        else:
            self.conn = sqlite3.connect(self.db_file)
        try:
            # enforce foreign key constraints on this connection
            self.conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error:
            # ignore if pragma not supported for some reason
            pass
        return self.conn

    def init_db(self):
        """
        Ensure the database exists and initialize it if missing.

        For an in-memory database (`:memory:`) the schema must be applied on
        every new connection, so we call `init_new_db()` when using
        `:memory:` or when the database file does not yet exist on disk.
        """
        if self.db_file == ':memory:' or not os.path.exists(self.db_file):
            self.init_new_db()

    def init_new_db(self):
        """
        Create a new database by executing the SQL script configured in
        `self.sql_file`.

        The method opens a connection, reads the SQL file and executes it
        with `cursor.executescript()`, then commits the changes. The
        connection is closed in a finally block.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()

            # init db via script
            with open(self.sql_file, encoding='utf-8') as sql_script:
                sql_as_string = sql_script.read()
                cur.executescript(sql_as_string)
            self.conn.commit()

        except sqlite3.Error as e:
            print(e)
        finally:
            self.close_connection()

    def insert_entry(self, entry):
        """
        Insert a single timesheet entry into the `dt_entry` table.

        Args:
            entry (dict): Entry data with the following possible keys:
                - entry_date (str): YYYY-MM-DD
                - start_time (str): HH:MM or HH:MM:SS
                - duration_minutes (int)
                - description (str)
                - notes (str)
                - category_id (int)
                - billable (0|1)
                - project_id (int)
                - company_id (int)

        Returns:
            None
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            # Accept a dict with the following keys:
            # entry_date, start_time, duration_minutes, description, notes, category_id, billable, project_id, company_id

            entry_date = entry.get('entry_date')
            start_time = entry.get('start_time')
            duration_minutes = int(entry.get('duration_minutes', 0) or 0)
            description = entry.get('description')
            notes = entry.get('notes')
            category_id = entry.get('category_id')
            billable = int(entry.get('billable', 0) or 0)
            project_id = entry.get('project_id')
            company_id = entry.get('company_id')

            query_str = (
                "INSERT INTO dt_entry (entry_date, start_time, duration_minutes, description, notes, category_id, project_id, company_id, billable) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            )
            cur.execute(query_str, (entry_date, start_time, duration_minutes, description, notes, category_id, project_id, company_id, billable))
            self.conn.commit()
        except sqlite3.Error as e:
            print(e)
        finally:
            self.close_connection()

    def get_categories(self):
        """
        Return all categories from `rt_category` as a list of dictionaries.

        Returns:
            list[dict]: Each dict contains `id`, `code`, and `description`.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            query_str = 'SELECT id, code, description FROM rt_category ORDER BY code ASC'
            cur.execute(query_str)
            rows = cur.fetchall()
            response = [{"id": r[0], "code": r[1], "description": r[2]} for r in rows]
        except sqlite3.Error as e:
            print(e)
            response = []
        finally:
            self.close_connection()
        return response

    def get_companies(self):
        """
        Return all companies from `rt_company` as a list of dictionaries.

        Returns:
            list[dict]: Each dict contains `id`, `name`, `description`, and `pay_rate`.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            query_str = 'SELECT id, name, description, pay_rate FROM rt_company ORDER BY name ASC'
            cur.execute(query_str)
            rows = cur.fetchall()
            response = [{"id": r[0], "name": r[1], "description": r[2], "pay_rate": r[3]} for r in rows]
        except sqlite3.Error as e:
            print(e)
            response = []
        finally:
            self.close_connection()
        return response

    def get_projects(self, company=None):
        """
        Return projects optionally filtered by company name.

        Args:
            company (str|None): If provided, only projects belonging to the
                company with this name are returned.

        Returns:
            list[dict]: Project dictionaries with keys `id`, `code`, `name`,
            `due_date`, `company_id`, `company_name`, and `description`.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            base_q = (
                'SELECT p.id, p.code, p.name, p.due_date, p.company_id, c.name as company_name, p.description '
                'FROM rt_project p LEFT JOIN rt_company c ON p.company_id = c.id '
            )
            params = None
            if company:
                query_str = base_q + 'WHERE c.name = ? ORDER BY p.code ASC'
                params = (company,)
                cur.execute(query_str, params)
            else:
                query_str = base_q + 'ORDER BY p.code ASC'
                cur.execute(query_str)
            rows = cur.fetchall()
            response = [
                {
                    "id": r[0],
                    "code": r[1],
                    "name": r[2],
                    "due_date": r[3],
                    "company_id": r[4],
                    "company_name": r[5],
                    "description": r[6]
                }
                for r in rows
            ]
        except sqlite3.Error as e:
            print(e)
            response = []
        finally:
            self.close_connection()
        return response

    def get_report_between(self, start, end, company_id=None, category_id=None, project_id=None):
        """
        Retrieve entries between `start` and `end` (inclusive).

        Args:
            start (str): Start date in YYYY-MM-DD format.
            end (str): End date in YYYY-MM-DD format.
            company_id (int|None): Optional company id filter.
            category_id (int|None): Optional category id filter.
            project_id (int|None): Optional project id filter.

        Returns:
            list[tuple]: Rows returned from the `vt_entry_with_end` view.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            # build query with optional filters
            conditions = ["entry_date BETWEEN ? AND ?"]
            params = [start, end]
            if company_id is not None:
                conditions.append("company_id = ?")
                params.append(company_id)
            if category_id is not None:
                conditions.append("category_id = ?")
                params.append(category_id)
            if project_id is not None:
                conditions.append("project_id = ?")
                params.append(project_id)

            query_str = f"SELECT * FROM vt_entry_with_end WHERE {' AND '.join(conditions)} ORDER BY entry_date ASC, start_time ASC"
            cur.execute(query_str, params)
            response = cur.fetchall()
        except sqlite3.Error as e:
            print(e)
        finally:
            self.close_connection()
        return response

    def get_report_all(self):
        """
        Return all entries from the `vt_entry_with_end` view ordered by date
        and start time.

        Returns:
            list[tuple]: All rows from the view.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            query_str = 'SELECT * FROM vt_entry_with_end ORDER BY entry_date ASC, start_time ASC'
            cur.execute(query_str)
            response = cur.fetchall()
        except sqlite3.Error as e:
            print(e)
        finally:
            self.close_connection()
        return response

    def get_hours_and_pay(self, start, end, company_id, category_id=None, project_id=None):
        """
        Calculate total hours and pay for a company between given dates.

        Args:
            start (str): Start date (YYYY-MM-DD).
            end (str): End date (YYYY-MM-DD).
            company_id (int): Company id to aggregate for.
            category_id (int|None): Optional category filter.
            project_id (int|None): Optional project filter.

        Returns:
            dict: {"hours": float, "pay": float} where `hours` is the
            total hours (duration_minutes / 60) and `pay` is hours * pay_rate.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            # Build the WHERE clause with optional filters
            conditions = ['e.entry_date BETWEEN ? AND ?', 'e.company_id = ?']
            params = [start, end, company_id]
            
            if category_id is not None:
                conditions.append('e.category_id = ?')
                params.append(category_id)
            if project_id is not None:
                conditions.append('e.project_id = ?')
                params.append(project_id)
            
            where_clause = ' AND '.join(conditions)
            
            # Get total minutes and pay rate for the company
            query_str = (
                'SELECT SUM(e.duration_minutes) as total_minutes, co.pay_rate '
                'FROM dt_entry e LEFT JOIN rt_company co ON e.company_id = co.id '
                f'WHERE {where_clause} '
                'GROUP BY e.company_id'
            )
            cur.execute(query_str, params)
            row = cur.fetchone()
            
            if row and row[0]:
                total_minutes = row[0]
                pay_rate = row[1] or 0.0
                total_hours = total_minutes / 60.0
                total_pay = total_hours * pay_rate
                response = {"hours": total_hours, "pay": total_pay}
            else:
                response = {"hours": 0.0, "pay": 0.0}
        except sqlite3.Error as e:
            print(e)
            response = {"hours": 0.0, "pay": 0.0}
        finally:
            self.close_connection()
        return response

    def delete_entry(self, entry_id=None, entry_date=None, start_time=None):
        """
        Delete a timesheet entry by ID or by entry_date and start_time.
        
        Args:
            entry_id: The ID of the entry to delete
            entry_date: The date of the entry (YYYY-MM-DD) - use with start_time
            start_time: The start time of the entry (HH:MM or HH:MM:SS) - use with entry_date
        
        Returns True if successful, False otherwise.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            
            if entry_id is not None:
                # Delete by ID
                query_str = "DELETE FROM dt_entry WHERE id = ?"
                cur.execute(query_str, (entry_id,))
            elif entry_date is not None and start_time is not None:
                # Delete by entry_date and start_time
                query_str = "DELETE FROM dt_entry WHERE entry_date = ? AND start_time = ?"
                cur.execute(query_str, (entry_date, start_time))
            else:
                # Invalid parameters
                return False
            
            self.conn.commit()
            return cur.rowcount > 0
        except sqlite3.Error as e:
            print(e)
            return False
        finally:
            self.close_connection()

    def add_category(self, code, description=None):
        """
        Create a new category row in `rt_category`.

        Args:
            code (str): Category code (unique).
            description (str|None): Optional description.

        Returns:
            int|None: New category id on success, or None on failure.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            query_str = 'INSERT INTO rt_category (code, description) VALUES (?, ?)'
            cur.execute(query_str, (code, description))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            # unique constraint failed or other integrity issue
            return None
        except sqlite3.Error as e:
            print(e)
            return None
        finally:
            self.close_connection()

    def remove_category(self, category_id=None, code=None):
        """
        Delete a category by `id` or `code`.

        Args:
            category_id (int|None): ID of the category to remove.
            code (str|None): Code of the category to remove.

        Returns:
            bool: True if a row was deleted, False otherwise (including FK
            constraint violations).
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            if category_id is not None:
                query_str = 'DELETE FROM rt_category WHERE id = ?'
                cur.execute(query_str, (category_id,))
            elif code is not None:
                query_str = 'DELETE FROM rt_category WHERE code = ?'
                cur.execute(query_str, (code,))
            else:
                return False
            self.conn.commit()
            return cur.rowcount > 0
        except sqlite3.IntegrityError:
            # foreign key prevents deletion
            return False
        except sqlite3.Error as e:
            print(e)
            return False
        finally:
            self.close_connection()

    def add_company(self, name, description=None, pay_rate=0.0):
        """
        Insert a new company into `rt_company`.

        Args:
            name (str): Company name (should be unique).
            description (str|None): Optional description.
            pay_rate (float): Hourly pay rate.

        Returns:
            int|None: New company id on success, or None on failure.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            query_str = 'INSERT INTO rt_company (name, description, pay_rate) VALUES (?, ?, ?)'
            cur.execute(query_str, (name, description, float(pay_rate)))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None
        except sqlite3.Error as e:
            print(e)
            return None
        finally:
            self.close_connection()

    def remove_company(self, company_id=None, name=None):
        """
        Delete a company by `id` or `name`.

        Args:
            company_id (int|None): ID of the company to remove.
            name (str|None): Name of the company to remove.

        Returns:
            bool: True if a row was deleted, False otherwise.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            if company_id is not None:
                query_str = 'DELETE FROM rt_company WHERE id = ?'
                cur.execute(query_str, (company_id,))
            elif name is not None:
                query_str = 'DELETE FROM rt_company WHERE name = ?'
                cur.execute(query_str, (name,))
            else:
                return False
            self.conn.commit()
            return cur.rowcount > 0
        except sqlite3.IntegrityError:
            return False
        except sqlite3.Error as e:
            print(e)
            return False
        finally:
            self.close_connection()

    def update_entry(self, entry_id=None, entry_date=None, start_time=None, update_fields=None):
        """
        Update a timesheet entry identified by `entry_id` or by `entry_date`
        and `start_time`.

        Args:
            entry_id (int|None): Primary key id of the entry to update.
            entry_date (str|None): Date of the entry (use with `start_time`).
            start_time (str|None): Start time of the entry (use with `entry_date`).
            update_fields (dict): Mapping of column names to new values. Allowed
                keys: entry_date, start_time, duration_minutes, description,
                notes, category_id, project_id, company_id, billable.

        Returns:
            bool: True if a row was updated, False otherwise.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()

            if not update_fields:
                return False

            allowed = [
                'entry_date', 'start_time', 'duration_minutes', 'description', 'notes',
                'category_id', 'project_id', 'company_id', 'billable'
            ]

            set_parts = []
            params = []
            for k in allowed:
                if k in update_fields:
                    set_parts.append(f"{k} = ?")
                    params.append(update_fields[k])

            if not set_parts:
                return False

            if entry_id is not None:
                query_str = f"UPDATE dt_entry SET {', '.join(set_parts)} WHERE id = ?"
                params.append(entry_id)
            elif entry_date is not None and start_time is not None:
                query_str = f"UPDATE dt_entry SET {', '.join(set_parts)} WHERE entry_date = ? AND start_time = ?"
                params.append(entry_date)
                params.append(start_time)
            else:
                return False

            cur.execute(query_str, tuple(params))
            self.conn.commit()
            return cur.rowcount > 0
        except sqlite3.Error as e:
            print(e)
            return False
        finally:
            self.close_connection()

    def update_company(self, company_id=None, name=None, update_fields=None):
        """
        Update company metadata identified by `company_id` or `name`.

        Args:
            company_id (int|None): Company id to update.
            name (str|None): Company name to update (if id not provided).
            update_fields (dict): Fields to update. Allowed keys: name,
                description, pay_rate.

        Returns:
            bool: True if a row was updated, False otherwise.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()

            if not update_fields:
                return False

            allowed = ['name', 'description', 'pay_rate']
            set_parts = []
            params = []
            for k in allowed:
                if k in update_fields:
                    set_parts.append(f"{k} = ?")
                    params.append(update_fields[k])

            if not set_parts:
                return False

            if company_id is not None:
                query_str = f"UPDATE rt_company SET {', '.join(set_parts)} WHERE id = ?"
                params.append(company_id)
            elif name is not None:
                query_str = f"UPDATE rt_company SET {', '.join(set_parts)} WHERE name = ?"
                params.append(name)
            else:
                return False

            cur.execute(query_str, tuple(params))
            self.conn.commit()
            return cur.rowcount > 0
        except sqlite3.IntegrityError:
            return False
        except sqlite3.Error as e:
            print(e)
            return False
        finally:
            self.close_connection()

    def update_category(self, category_id=None, code=None, update_fields=None):
        """
        Update category information identified by `category_id` or `code`.

        Args:
            category_id (int|None): Category id to update.
            code (str|None): Category code to update (if id not provided).
            update_fields (dict): Fields to update. Allowed keys: code,
                description.

        Returns:
            bool: True if a row was updated, False otherwise.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()

            if not update_fields:
                return False

            allowed = ['code', 'description']
            set_parts = []
            params = []
            for k in allowed:
                if k in update_fields:
                    set_parts.append(f"{k} = ?")
                    params.append(update_fields[k])

            if not set_parts:
                return False

            if category_id is not None:
                query_str = f"UPDATE rt_category SET {', '.join(set_parts)} WHERE id = ?"
                params.append(category_id)
            elif code is not None:
                query_str = f"UPDATE rt_category SET {', '.join(set_parts)} WHERE code = ?"
                params.append(code)
            else:
                return False

            cur.execute(query_str, tuple(params))
            self.conn.commit()
            return cur.rowcount > 0
        except sqlite3.IntegrityError:
            return False
        except sqlite3.Error as e:
            print(e)
            return False
        finally:
            self.close_connection()

    def update_project(self, project_id=None, code=None, update_fields=None):
        """
        Update project data identified by `project_id` or `code`.

        Args:
            project_id (int|None): Project id to update.
            code (str|None): Project code to update (if id not provided).
            update_fields (dict): Fields to update. Allowed keys: code,
                name, due_date, company_id, description.

        Returns:
            bool: True if a row was updated, False otherwise.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()

            if not update_fields:
                return False

            allowed = ['code', 'name', 'due_date', 'company_id', 'description']
            set_parts = []
            params = []
            for k in allowed:
                if k in update_fields:
                    set_parts.append(f"{k} = ?")
                    params.append(update_fields[k])

            if not set_parts:
                return False

            if project_id is not None:
                query_str = f"UPDATE rt_project SET {', '.join(set_parts)} WHERE id = ?"
                params.append(project_id)
            elif code is not None:
                query_str = f"UPDATE rt_project SET {', '.join(set_parts)} WHERE code = ?"
                params.append(code)
            else:
                return False

            cur.execute(query_str, tuple(params))
            self.conn.commit()
            return cur.rowcount > 0
        except sqlite3.IntegrityError:
            return False
        except sqlite3.Error as e:
            print(e)
            return False
        finally:
            self.close_connection()

    def add_project(self, code, name=None, due_date=None, company_id=None, description=None):
        """
        Insert a new project into `rt_project`.

        Args:
            code (str): Project code (unique).
            name (str|None): Optional project name.
            due_date (str|None): Optional due date (YYYY-MM-DD).
            company_id (int|None): Optional owning company id.
            description (str|None): Optional description.

        Returns:
            int|None: New project id on success, or None on failure.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            query_str = 'INSERT INTO rt_project (code, name, due_date, company_id, description) VALUES (?, ?, ?, ?, ?)'
            cur.execute(query_str, (code, name, due_date, company_id, description))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None
        except sqlite3.Error as e:
            print(e)
            return None
        finally:
            self.close_connection()

    def remove_project(self, project_id=None, code=None):
        """
        Delete a project by `id` or `code`.

        Args:
            project_id (int|None): ID of the project to remove.
            code (str|None): Code of the project to remove.

        Returns:
            bool: True if a row was deleted, False otherwise.
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            if project_id is not None:
                query_str = 'DELETE FROM rt_project WHERE id = ?'
                cur.execute(query_str, (project_id,))
            elif code is not None:
                query_str = 'DELETE FROM rt_project WHERE code = ?'
                cur.execute(query_str, (code,))
            else:
                return False
            self.conn.commit()
            return cur.rowcount > 0
        except sqlite3.IntegrityError:
            return False
        except sqlite3.Error as e:
            print(e)
            return False
        finally:
            self.close_connection()
