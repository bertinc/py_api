from pathlib import Path

import pytest

from db import TimesheetDB


HERE = Path(__file__).resolve().parents[1]


def prepare_env(tmp_path: Path):
    """Copy the SQL init script into the temp dir and return paths.

    Returns (db_file, sql_file) as strings.
    """
    sql_src = HERE / "init_timesheet_db.sql"
    sql_dst = tmp_path / "init_timesheet_db.sql"
    sql_dst.write_text(sql_src.read_text(encoding="utf-8"), encoding="utf-8")
    db_file = tmp_path / "timesheet.db"
    return str(db_file), str(sql_dst)


def test_init_and_seed(tmp_path):
    db_file, sql_file = prepare_env(tmp_path)
    db = TimesheetDB(db_file=db_file, sql_file=sql_file)
    db.init_db()

    # DB file should exist on disk
    assert Path(db_file).exists()

    cats = db.get_categories()
    assert any(c["code"] == "DEV" for c in cats) or any(c["code"] == "DEV" for c in cats)

    companies = db.get_companies()
    assert any(co["name"] == "Wasatch Photonics" for co in companies)


def test_crud_and_report(tmp_path):
    db_file, sql_file = prepare_env(tmp_path)
    db = TimesheetDB(db_file=db_file, sql_file=sql_file)
    db.init_db()

    new_company_id = db.add_company("TestCo", "desc", pay_rate=20.0)
    assert isinstance(new_company_id, int)

    new_cat_id = db.add_category("TST", "test category")
    assert isinstance(new_cat_id, int)

    new_proj_id = db.add_project("TST_PROJ", name="Test Project", company_id=new_company_id)
    assert isinstance(new_proj_id, int)

    entry = {
        "entry_date": "2026-02-01",
        "start_time": "09:00",
        "duration_minutes": 120,
        "description": "Test work",
        "notes": "none",
        "category_id": new_cat_id,
        "billable": 1,
        "project_id": new_proj_id,
        "company_id": new_company_id,
    }
    db.insert_entry(entry)

    rows = db.get_report_between("2026-02-01", "2026-02-01", company_id=new_company_id)
    assert len(rows) == 1

    hp = db.get_hours_and_pay("2026-02-01", "2026-02-01", new_company_id)
    assert pytest.approx(hp["hours"], rel=1e-6) == 2.0
    assert pytest.approx(hp["pay"], rel=1e-6) == 2.0 * 20.0

    entry_id = rows[0][0]
    updated = db.update_entry(entry_id=entry_id, update_fields={"duration_minutes": 60})
    assert updated is True

    rows2 = db.get_report_between("2026-02-01", "2026-02-01", company_id=new_company_id)
    assert rows2[0][3] == 60

    deleted = db.delete_entry(entry_id=entry_id)
    assert deleted is True
    rows3 = db.get_report_between("2026-02-01", "2026-02-01", company_id=new_company_id)
    assert rows3 == []


def test_delete_constraints(tmp_path):
    db_file, sql_file = prepare_env(tmp_path)
    db = TimesheetDB(db_file=db_file, sql_file=sql_file)
    db.init_db()

    cats = db.get_categories()
    dev = next((c for c in cats if c["code"] == "DEV"), None)
    assert dev is not None

    company_id = db.add_company("DeleteTestCo")
    entry = {
        "entry_date": "2026-02-02",
        "start_time": "10:00",
        "duration_minutes": 30,
        "category_id": dev["id"],
        "company_id": company_id,
    }
    db.insert_entry(entry)

    removed = db.remove_category(category_id=dev["id"])
    assert removed is False
