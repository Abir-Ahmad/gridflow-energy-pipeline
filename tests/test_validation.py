from datetime import date
import pytest
from gridflow.validate import validate_file, period_limit
from gridflow.models import HEADERS


def test_real_fixture_and_signed_flows(write_csv, source_rows):
    rows, rejected, total = validate_file(write_csv(source_rows), "a" * 64)
    assert total == len(rows) == 4
    assert not rejected
    assert rows[0]["settlement_date"] == date(2024, 1, 1)
    assert rows[0]["moyle_flow"] == -179
    assert rows[0]["national_demand_mw"] == 21783

@pytest.mark.parametrize("field,value,reason", [
    ("SETTLEMENT_DATE", "31-FEB-2024", "invalid_date"),
    ("SETTLEMENT_PERIOD", "0", "invalid_settlement_period"),
    ("SETTLEMENT_PERIOD", "49", "invalid_settlement_period"),
    ("SETTLEMENT_PERIOD", "1.5", "invalid_settlement_period"),
    ("ND", "", "invalid_integer:ND"),
    ("TSD", "nan", "invalid_integer:TSD"),
    ("ND", "12.3", "invalid_integer:ND"),
    ("ND", str(2**31), "integer_out_of_range:ND"),
])
def test_bad_rows_quarantined(write_csv, source_rows, field, value, reason):
    source_rows[0][field] = value
    valid, rejected, total = validate_file(write_csv(source_rows), "a" * 64)
    assert total == 4 and len(valid) == 3 and len(rejected) == 1
    assert reason in rejected[0]["reasons"]
    assert rejected[0]["source_line"] == 2


def test_duplicates_all_quarantined(write_csv, source_rows):
    source_rows.append(dict(source_rows[0], ND="999"))
    valid, rejected, total = validate_file(write_csv(source_rows), "a" * 64)
    assert total == 5 and len(valid) == 3
    assert len(rejected) == 2
    assert all("duplicate_business_key" in r["reasons"] for r in rejected)


def test_bad_headers_fail_whole_batch(write_csv):
    with pytest.raises(ValueError, match="header_mismatch"):
        validate_file(write_csv([], HEADERS[:-1]), "x")


def test_dst_bounds(write_csv, source_rows):
    assert period_limit(date(2024, 3, 31)) == 46
    assert period_limit(date(2024, 10, 27)) == 50
    for day, period, accepted in [("31-MAR-2024", "46", True), ("31-MAR-2024", "47", False),
                                  ("27-OCT-2024", "50", True), ("27-OCT-2024", "51", False)]:
        row = dict(source_rows[0], SETTLEMENT_DATE=day, SETTLEMENT_PERIOD=period)
        valid, rejected, _ = validate_file(write_csv([row]), "x")
        assert bool(valid) == accepted
        assert bool(rejected) != accepted


def test_malformed_csv_row(write_csv, source_rows):
    path = write_csv(source_rows[:1])
    with path.open("a") as f:
        f.write("01-JAN-2024,2,300\n")
    valid, rejected, total = validate_file(path, "x")
    assert total == 2 and len(valid) == 1
    assert "malformed_row" in rejected[0]["reasons"]
