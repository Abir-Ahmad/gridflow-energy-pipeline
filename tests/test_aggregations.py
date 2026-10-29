from pathlib import Path
from sqlalchemy import create_engine
from gridflow.load import load_records
from gridflow.validate import validate_file


def test_queries_against_known_real_fixture(write_csv, source_rows, database_url):
    rows, _, _ = validate_file(write_csv(source_rows), "a" * 64)
    load_records(database_url, rows)
    queries = (Path(__file__).parents[1] / 'sql/analysis_queries.sql').read_text().split(';')
    engine = create_engine(database_url)
    with engine.connect() as c:
        monthly = c.exec_driver_sql(queries[0]).mappings().all()
        profile = c.exec_driver_sql(queries[1]).mappings().all()
        daily = c.exec_driver_sql(queries[2]).mappings().all()
    assert len(monthly) == 1 and monthly[0]['month'] == '2024-01'
    assert monthly[0]['periods'] == 4
    assert monthly[0]['avg_demand_mw'] == sum(int(r['ND']) for r in source_rows) / 4
    assert monthly[0]['peak_demand_mw'] == max(int(r['ND']) for r in source_rows)
    assert len(profile) == 4 and profile[0]['avg_embedded_wind_mw'] == 2804
    assert len(daily) == 1 and daily[0]['periods'] == 4
    engine.dispose()
