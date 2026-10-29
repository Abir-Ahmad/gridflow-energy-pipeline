"""Reproduce real-data rerun, controlled overlap and rejection evidence.
Run from repository root after the documented initial full load.
"""
import csv
import json
from pathlib import Path
import sqlite3
from gridflow.cli import run


def write(path, rows, headers):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)


def main():
    evidence = Path('evidence')
    evidence.mkdir(exist_ok=True)
    with Path('data/raw/demanddata_2024.csv').open() as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)
    rerun = run('data/raw/demanddata_2024.csv', 'sqlite:///gridflow.db')
    demo = Path('artifacts/demo')
    demo.mkdir(parents=True, exist_ok=True)
    db = demo / 'overlap.db'
    if db.exists():
        db.unlink()  # Dedicated disposable demonstration only.
    write(demo / 'first.csv', rows[:3], headers)
    initial = run(demo / 'first.csv', 'sqlite:///' + str(db))
    overlap = [dict(r) for r in rows[:4]]
    overlap[0]['ND'] = str(int(overlap[0]['ND']) + 1)
    write(demo / 'overlap.csv', overlap, headers)
    second = run(demo / 'overlap.csv', 'sqlite:///' + str(db))
    bad = [dict(r) for r in rows[:4]]
    bad[0]['ND'] = 'INVALID_FOR_QUARANTINE_DEMO'
    write(demo / 'invalid.csv', bad, headers)
    rejection = run(demo / 'invalid.csv', 'sqlite:///' + str(db))
    assert (rerun['inserted'], rerun['updated'], rerun['skipped'], rerun['rejected']) == (0, 0, len(rows), 0)
    assert (second['inserted'], second['updated'], second['skipped']) == (1, 1, 2)
    assert rejection['rejected'] == 1 and rejection['exit_code'] == 2
    with sqlite3.connect('gridflow.db') as c:
        count, unique = c.execute("SELECT count(*), count(DISTINCT settlement_date || ':' || settlement_period) FROM energy_records").fetchone()
        assert count == unique == len(rows)
        queries = Path('sql/analysis_queries.sql').read_text().split(';')
        for name, query in zip(['monthly', 'period_profile', 'daily'], queries):
            cur = c.execute(query)
            with (evidence / (name + '.csv')).open('w', newline='') as f:
                w = csv.writer(f)
                w.writerow([d[0] for d in cur.description])
                w.writerows(cur.fetchall())
        summary = c.execute('SELECT avg(national_demand_mw), max(national_demand_mw), max(embedded_solar_generation), max(embedded_wind_generation) FROM energy_records').fetchone()
    result = {'rerun': rerun, 'overlap_initial': initial, 'overlap_second': second,
              'invalid_demo': rejection, 'verified_full_database_rows': count,
              'unique_keys': unique,
              'full_year_measures': dict(zip(['avg_demand_mw','peak_demand_mw','peak_embedded_solar_mw','peak_embedded_wind_mw'], summary)),
              'correction_note': 'Controlled demo changes first official ND value by +1 MW in a separate database. Not a claim of an official correction.'}
    (evidence / 'demonstrations.json').write_text(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
