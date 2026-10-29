"""One atomic upsert transaction per validated batch (single writer v1)."""
from sqlalchemy import create_engine, select
from .models import energy, metadata


def load_records(database_url, rows):
    engine = create_engine(database_url)
    try:
        if engine.dialect.name not in ("sqlite", "postgresql"):
            raise ValueError("unsupported_database: use SQLite or PostgreSQL")
        metadata.create_all(engine)
        if engine.dialect.name == "sqlite":
            from sqlalchemy.dialects.sqlite import insert
        else:
            from sqlalchemy.dialects.postgresql import insert
        with engine.begin() as conn:
            existing = {(r.settlement_date, r.settlement_period): r.record_hash
                        for r in conn.execute(select(energy.c.settlement_date,
                                                     energy.c.settlement_period,
                                                     energy.c.record_hash))}
            inserted = updated = skipped = 0
            changes = []
            for row in rows:
                old = existing.get((row["settlement_date"], row["settlement_period"]))
                if old == row["record_hash"]:
                    skipped += 1
                else:
                    if old is None:
                        inserted += 1
                    else:
                        updated += 1
                    changes.append(row)
            statement = insert(energy)
            statement = statement.on_conflict_do_update(
                index_elements=[energy.c.settlement_date, energy.c.settlement_period],
                set_={c.name: getattr(statement.excluded, c.name)
                      for c in energy.columns if not c.primary_key})
            # Executemany keeps SQLite's bound-variable count small.
            if changes:
                conn.execute(statement, changes)
        return {"inserted": inserted, "updated": updated, "skipped": skipped}
    finally:
        engine.dispose()
