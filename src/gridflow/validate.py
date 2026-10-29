"""Strict source validation; invalid rows are quarantined, never filled."""
import calendar
from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
import re
from .models import HEADERS, NAMES


def parse_date(value):
    for fmt in ("%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except (ValueError, TypeError):
            pass
    raise ValueError("invalid_date")


def period_limit(day):
    # UK clock changes: last Sunday in March/October; no UTC approximation.
    last_sunday = max(w[calendar.SUNDAY] for w in calendar.monthcalendar(day.year, day.month))
    if day.day == last_sunday and day.month in (3, 10):
        return 46 if day.month == 3 else 50
    return 48


def business_key(row):
    day = parse_date(row.get("SETTLEMENT_DATE"))
    value = row.get("SETTLEMENT_PERIOD") or ""
    if not re.fullmatch(r"\d+", value.strip()):
        raise ValueError("invalid_settlement_period")
    period = int(value)
    if not 1 <= period <= period_limit(day):
        raise ValueError("invalid_settlement_period")
    return day, period


def validate_file(path, checksum):
    with open(path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != HEADERS:
            raise ValueError("header_mismatch: expected the documented 22 source columns in order")
        rows = list(reader)
    keys = []
    for row in rows:
        try:
            keys.append(business_key(row))
        except ValueError:
            keys.append(None)
    counts = Counter(k for k in keys if k is not None)
    valid, rejected = [], []
    for line, (row, key) in enumerate(zip(rows, keys), start=2):
        reasons = []
        if None in row or any(v is None for v in row.values()):
            reasons.append("malformed_row")
        if key is None:
            try:
                business_key(row)
            except ValueError as error:
                reasons.append(str(error))
        elif counts[key] > 1:
            reasons.append("duplicate_business_key")
        measures = {}
        for h in HEADERS[2:]:
            v = row.get(h) or ""
            if not re.fullmatch(r"[+-]?\d+", v.strip()):
                reasons.append("invalid_integer:" + h)
            else:
                number = int(v)
                if not -(2**31) <= number < 2**31:
                    reasons.append("integer_out_of_range:" + h)
                measures[NAMES[h]] = number
        if reasons:
            rejected.append({"source_line": line, "reasons": reasons, "raw_record": row})
            continue
        day, period = key
        canonical = {"settlement_date": day.isoformat(), "settlement_period": period, **measures}
        digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
        valid.append({**canonical, "settlement_date": day, "record_hash": digest,
                      "source_sha256": checksum, "source_line": line,
                      "raw_record": json.dumps(row, sort_keys=True)})
    return valid, rejected, len(rows)
