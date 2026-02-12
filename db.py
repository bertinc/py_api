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

    def insert_entry(self, entry):
        """
        Insert a single timesheet entry into the database
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

    def get_report_between(self, start, end, company_id=None, category_id=None, project_id=None):
        """
        Get all entries between the provided start and end dates
        Note: BETWEEN is inclusive of start and end
        Filters by company_id, category_id, and/or project_id if provided
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

    def get_hours_and_pay(self, start, end, company_id, category_id=None, project_id=None):
        """
        Get total hours and pay for a company between the provided start and end dates
        Optionally filter by category_id and/or project_id
        Returns a dict with 'hours' and 'pay' (hours * pay_rate)
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
