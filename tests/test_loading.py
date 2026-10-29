import json
import sqlite3
from datetime import date
from sqlalchemy import create_engine, select, event
from sqlalchemy.exc import IntegrityError
import pytest
from gridflow.cli import run
from gridflow.load import load_records
from gridflow.models import energy
from gridflow.validate import validate_file


def test_idempotency_and_provenance(write_csv, source_rows, database_url, tmp_path):
    path = write_csv(source_rows)
    first = run(path, database_url, tmp_path / "artifacts")
    second = run(path, database_url, tmp_path / "artifacts")
    assert first["inserted"] == 4 and first["exit_code"] == 0
    assert second["inserted"] == second["updated"] == second["rejected"] == 0
    assert second["skipped"] == 4 and second["exit_code"] == 0
    assert first["source_sha256"] == second["source_sha256"]
    assert json.loads(open(second["report_file"]).read())["skipped"] == 4
    assert open(second["raw_file"], "rb").read() == path.read_bytes()
    engine = create_engine(database_url)
    with engine.connect() as c:
        assert len(c.execute(select(energy)).all()) == 4
    # Database constraint, independently of application validation.
    rows, _, _ = validate_file(path, "a" * 64)
    with pytest.raises(IntegrityError), engine.begin() as c:
        c.execute(energy.insert(), rows[0])
    engine.dispose()


def test_incremental_insert_update_skip(write_csv, source_rows, database_url):
    first, _, _ = validate_file(write_csv(source_rows[:2]), "a" * 64)
    assert load_records(database_url, first) == {"inserted": 2, "updated": 0, "skipped": 0}
    source_rows[0]["ND"] = "22000"
    second, _, _ = validate_file(write_csv(source_rows[:3]), "b" * 64)
    assert load_records(database_url, second) == {"inserted": 1, "updated": 1, "skipped": 1}
    engine = create_engine(database_url)
    with engine.connect() as c:
        rows = c.execute(select(energy).order_by(energy.c.settlement_period)).mappings().all()
    assert [r["national_demand_mw"] for r in rows] == [22000, 22521, int(source_rows[2]["ND"])]
    assert rows[0]["source_sha256"] == "b" * 64
    assert rows[1]["source_sha256"] == "a" * 64
    engine.dispose()


def test_transaction_rolls_back_mid_batch(write_csv, source_rows, database_url):
    rows, _, _ = validate_file(write_csv(source_rows[:1]), "a" * 64)
    load_records(database_url, rows)
    engine = create_engine(database_url)
    with engine.begin() as c:
        c.exec_driver_sql("CREATE TRIGGER fail_third BEFORE INSERT ON energy_records "
                          "WHEN NEW.settlement_period = 3 BEGIN SELECT RAISE(ABORT, 'test failure'); END")
    rows, _, _ = validate_file(write_csv(source_rows), "b" * 64)
    rows[0]["national_demand_mw"] = 999
    rows[0]["record_hash"] = "c" * 64
    with pytest.raises(IntegrityError):
        load_records(database_url, rows)
    with engine.connect() as c:
        persisted = c.execute(select(energy)).mappings().all()
    assert len(persisted) == 1
    assert persisted[0]["national_demand_mw"] == 21783
    engine.dispose()


def test_partial_rejection_reports(write_csv, source_rows, database_url, tmp_path):
    source_rows[0]["ND"] = "bad"
    report = run(write_csv(source_rows), database_url, tmp_path / "artifacts")
    assert report["exit_code"] == 2 and report["rejected"] == 1
    assert report["inserted"] == 3 and report["status"] == "completed_with_rejections"
    reject_path = __import__('pathlib').Path(report['report_file']).with_name('rejected.json')
    assert json.loads(reject_path.read_text())[0]["reasons"] == ["invalid_integer:ND"]


def test_missing_source_reports_failure(database_url, tmp_path):
    report = run(tmp_path / "missing.csv", database_url, tmp_path / "artifacts")
    assert report["exit_code"] == 1 and report["status"] == "failed"
    assert report["inserted"] == 0


def test_database_failure_no_success_counts(write_csv, source_rows, tmp_path):
    report = run(write_csv(source_rows), "sqlite:///" + str(tmp_path / 'missing' / 'x.db'), tmp_path / "artifacts")
    assert report["status"] == "failed" and report["inserted"] == 0
    assert report["error"] == "OperationalError"


def test_header_failure_no_load(write_csv, database_url, tmp_path):
    report = run(write_csv([], ["WRONG"]), database_url, tmp_path / "artifacts")
    assert report["exit_code"] == 1 and "header_mismatch" in report["error"]
    assert not (tmp_path / "test.db").exists()
