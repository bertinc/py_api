PRAGMA foreign_keys = ON;

-- Categories: use surrogate `id` for stability and easier updates
DROP TABLE IF EXISTS dt_entry;
DROP TABLE IF EXISTS rt_category;

CREATE TABLE rt_category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(30) NOT NULL UNIQUE,
    description TEXT
);

-- Seed categories (preserves original codes/descriptions)
INSERT INTO rt_category (code, description) VALUES
    ('DEV', 'application and database development'),
    ('FILM', 'film production or research and development'),
    ('IMAGING', 'anything to do with image process development or production work'),
    ('IT', 'administration of computer hardware or software services'),
    ('WET', 'wet processing development or production work'),
    ('SETUP', 'any time spent physically setting up a work space or environment'),
    ('MISC', 'stuff that cannot or does not need to be categorized'),
    ('COLAB', 'planning, administrative, brainstorming, and team building'),
    ('NONE', 'instead of erroring out, we will use this when an invalid category is entered');

-- Entries: normalized date/time fields, duration in minutes, and audit timestamps
CREATE TABLE dt_entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date DATE NOT NULL,
    start_time TIME NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 0 CHECK(duration_minutes >= 0),
    description TEXT,
    notes TEXT,
    category_id INTEGER NOT NULL,
    project_id INTEGER,
    company_id INTEGER,
    billable INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME,
    FOREIGN KEY(category_id) REFERENCES rt_category(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY(project_id) REFERENCES rt_project(id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY(company_id) REFERENCES rt_company(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- Helpful indexes for common queries
CREATE INDEX IF NOT EXISTS idx_dt_entry_date ON dt_entry(entry_date);
CREATE INDEX IF NOT EXISTS idx_dt_entry_category ON dt_entry(category_id);
CREATE INDEX IF NOT EXISTS idx_dt_entry_project ON dt_entry(project_id);
CREATE INDEX IF NOT EXISTS idx_dt_entry_company ON dt_entry(company_id);

-- View that computes an end_time for convenience
CREATE VIEW IF NOT EXISTS vt_entry_with_end AS
SELECT
    e.id,
    e.entry_date,
    e.start_time,
    e.duration_minutes,
    datetime(e.entry_date || ' ' || e.start_time, '+' || e.duration_minutes || ' minutes') AS end_time,
    e.description,
    e.notes,
    e.category_id,
    c.code AS category_code,
    c.description AS category_description,
    e.project_id,
    p.code AS project_code,
    p.name AS project_name,
    e.company_id,
    co.name AS company_name,
    e.billable,
    e.created_at,
    e.updated_at
FROM dt_entry e
LEFT JOIN rt_category c ON c.id = e.category_id
LEFT JOIN rt_project p ON p.id = e.project_id
LEFT JOIN rt_company co ON co.id = e.company_id;

-- Companies and Projects
CREATE TABLE rt_company (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    pay_rate REAL NOT NULL DEFAULT 0.0 -- hourly pay rate
);

-- Seed requested companies
INSERT INTO rt_company (name, description, pay_rate) VALUES
    ('Wasatch Photonics', 'Software Architect Consulting', 90.00),
    ('Elroy', 'Custom Software Development', 50.00);

CREATE TABLE rt_project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200),
    due_date DATE,
    company_id INTEGER,
    description TEXT,
    FOREIGN KEY(company_id) REFERENCES rt_company(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- Seed projects for seeded companies
INSERT INTO rt_project (code, name, company_id, description, due_date) VALUES
    ('GRATING_WEB_TOOL', 'Web Grating Design Tool', (SELECT id FROM rt_company WHERE name = 'Wasatch Photonics'), 'Design tool for grating web interfaces', NULL),
    ('ELROY_PRINTER_DEV', 'Grating Printer Designer', (SELECT id FROM rt_company WHERE name = 'Elroy'), 'Design tool for grating printer', NULL);