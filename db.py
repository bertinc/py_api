"""To make doing database operations easier"""
import sqlite3
import os
import constants as const

class TimesheetDB:
    """
    Does all the needed database interactions.
    """
    def __init__(self) -> None:
        self.file_path = const.PATH
        self.db_file = os.sep.join([self.file_path, const.DB_FILENAME])
        self.sql_file = os.sep.join([self.file_path, const.SQL_INIT_FILE])
        self.conn = None
        # map of category code -> id
        self.category_map = {}
        # map of project code -> id
        self.project_map = {}
        # map of company name -> id
        self.company_map = {}

    def close_connection(self):
        """
        Close the connection.
        """
        if self.conn:
            self.conn.close()

    def open_connection(self):
        """
        Open a sqlite3 connection and enable foreign key enforcement for this connection.
        """
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
        If a DB exists, open it. Else, initialize with the SQL script.
        """
        if not os.path.exists(self.db_file):
            self.init_new_db()
        # load lookup maps
        self.set_categories()
        self.set_projects()
        self.set_companies()

    def init_new_db(self):
        """
        Initialize the database from an SQL script.
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

    def insert_bulk_entries(self, entries):
        """
        Make a bulk insert of timesheet entries into the database
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            # Accept the normalized tuple format:
            # (entry_date, start_time, duration_minutes, description, notes, category_code, billable, project_code, company_key)
            prepared = []
            # ensure lookup maps are available
            if not getattr(self, 'category_map', None):
                self.set_categories()
            if not getattr(self, 'project_map', None):
                self.set_projects()
            if not getattr(self, 'company_map', None):
                self.set_companies()
            default_cat_id = self.category_map.get('NONE')

            for row in entries:
                entry_date = row[0]
                start_time = row[1] if len(row) > 1 else None
                duration_minutes = int(row[2]) if len(row) > 2 and row[2] is not None else 0
                description = row[3] if len(row) > 3 else None
                notes = row[4] if len(row) > 4 else None
                category_code = row[5] if len(row) > 5 else None
                billable = int(row[6]) if len(row) > 6 and row[6] is not None else 0
                project_code = row[7] if len(row) > 7 else None
                company_key = row[8] if len(row) > 8 else None

                cat_id = self.category_map.get(category_code) if category_code is not None else None
                if cat_id is None:
                    cat_id = default_cat_id

                project_id = self.project_map.get(project_code) if project_code is not None else None
                company_id = self.company_map.get(company_key) if company_key is not None else None

                prepared.append((entry_date, start_time, duration_minutes, description, notes, cat_id, project_id, company_id, billable))

            query_str = (
                "INSERT INTO dt_entry (entry_date, start_time, duration_minutes, description, notes, category_id, project_id, company_id, billable) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            )
            cur.executemany(query_str, prepared)
            self.conn.commit()
        except sqlite3.Error as e:
            print(e)
        finally:
            self.close_connection()

    def set_categories(self):
        """
        Load categories into `self.category_map` (code -> id).
        """
        response = []
        try:
            self.open_connection()
            cur = self.conn.cursor()

            query_str = 'SELECT id, code FROM rt_category'
            cur.execute(query_str)
            response = cur.fetchall()

            # build mapping: code -> id
            category_map = {code: cid for cid, code in response}
            self.category_map = category_map

        except sqlite3.Error as e:
            print(e)
        finally:
            self.close_connection()
        return response

    def set_projects(self):
        """
        Load projects into `self.project_map` (code -> id).
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            query_str = 'SELECT id, code FROM rt_project'
            cur.execute(query_str)
            response = cur.fetchall()
            project_map = {code: pid for pid, code in response}
            self.project_map = project_map
        except sqlite3.Error as e:
            print(e)
        finally:
            self.close_connection()
        return response

    def set_companies(self):
        """
        Load companies into `self.company_map` (name -> id).
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            query_str = 'SELECT id, name FROM rt_company'
            cur.execute(query_str)
            response = cur.fetchall()
            company_map = {name: cid for cid, name in response}
            self.company_map = company_map
        except sqlite3.Error as e:
            print(e)
        finally:
            self.close_connection()
        return response

    def get_categories(self):
        """
        Return list of categories as dicts with id, code, and description.
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
        Return list of companies as dicts with id, name, description, and pay_rate.
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
        Return list of projects. If `company` (company name) is provided,
        return projects for that company only.
        Each project dict includes id, code, name, due_date, company_id, company_name, description.
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

    def get_report_between(self, start, end, company=None, category=None, project=None):
        """
        Get all entries between the provided start and end dates
        Note: BETWEEN is inclusive of start and end
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            # build query with optional filters
            conditions = ["entry_date BETWEEN ? AND ?"]
            params = [start, end]
            if company:
                conditions.append("company_name = ?")
                params.append(company)
            if category:
                conditions.append("category_code = ?")
                params.append(category)
            if project:
                conditions.append("project_code = ?")
                params.append(project)

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
        Selects all entries
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

    def get_hours_by_category(self, start, end):
        """
        Sum hours by category accross date range
        """
        try:
            self.open_connection()
            cur = self.conn.cursor()
            # Sum minutes per category and return total hours as float
            query_str = (
                'SELECT c.code, SUM(e.duration_minutes) as total_minutes '
                'FROM dt_entry e JOIN rt_category c ON e.category_id = c.id '
                'WHERE entry_date BETWEEN ? AND ? '
                'GROUP BY c.code'
            )
            cur.execute(query_str, (start, end))
            raw = cur.fetchall()
            # convert minutes to hours (float)
            response = [(r[0], (r[1] or 0) / 60.0) for r in raw]
        except sqlite3.Error as e:
            print(e)
        finally:
            self.close_connection()
        return response
