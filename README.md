# GridFlow — GB Electricity Data Pipeline

A Python and SQL pipeline that validates, normalizes and incrementally loads
NESO electricity demand and embedded renewable generation data into SQLite or
PostgreSQL. Built around the official 2024 GB dataset, with a composite settlement
key, transactional upserts, rejected-row quarantine and auditable run reports.

**Locally verified:** 17,568 official records ingested; an identical rerun inserted
zero duplicates; controlled overlapping batches exercised inserts, updates and
unchanged rows. The supplied v1 suite passed **21 tests**. See
[verification evidence](docs/verification.md). PostgreSQL integration is untested.
For remote CI, inspect this repository's **Actions** tab; local test results do not
establish a GitHub Actions pass.

```mermaid
flowchart TD
    A[NESO CSV] --> B[Raw snapshot and SHA-256]
    B --> C[Validation and normalization]
    C --> D[Rejected rows with reasons]
    C --> E[Transactional upsert]
    E --> F[SQLite or PostgreSQL]
    F --> G[Analytical SQL]
    E --> H[JSON run report]
```

## Quick start

Python 3.10+ is required; the existing suite was tested on Python 3.12. SQLite needs
no separate database server, Docker or credentials. From the repository root:

```bash
python -m venv .venv
# Linux/macOS
.venv/bin/python -m pip install -e ".[test]"
.venv/bin/python -m pytest -q
.venv/bin/python -m gridflow tests/fixtures/sample.csv
.venv/bin/python -m gridflow tests/fixtures/sample.csv
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m gridflow tests/fixtures/sample.csv
.\.venv\Scripts\python.exe -m gridflow tests/fixtures/sample.csv
```

No virtual-environment activation is needed. The included fixture contains four
real NESO rows: a fresh first run inserts 4, the second skips 4. The CLI creates
`gridflow.db` in the current directory and retains inputs and reports in
`artifacts/`. These generated files are ignored by Git.

## Full official dataset

Download the CSV from [NESO Historic Demand Data 2024](https://www.neso.energy/data-portal/historic-demand-data/historic_demand_data_2024)
or its [official CSV endpoint](https://api.neso.energy/dataset/8f2fe0af-871c-488d-8bad-960426f24601/resource/f6d02c0f-957b-48cb-82ee-09003f2ba759/download/demanddata_2024.csv)
and save it as `data/raw/demanddata_2024.csv`. The complete raw CSV and preloaded
databases are intentionally excluded from this public source repository.

Using the virtual-environment Python (Windows example):

```powershell
.\.venv\Scripts\python.exe -m gridflow data/raw/demanddata_2024.csv --database-url sqlite:///full_2024.db
.\.venv\Scripts\python.exe -m gridflow data/raw/demanddata_2024.csv --database-url sqlite:///full_2024.db
```

The inspected 29 October 2026 download had 22 columns and 17,568 records. Its
SHA-256 was `fa7895b6e9ab5eb1b450949d969cb18ffeb6005359fc71c79c87e1c47e59cac6`.
Future NESO revisions may differ. Exact inspected headers and provenance are in
[evidence/source_inspection.json](evidence/source_inspection.json).
The CLI accepts local CSV paths; it does not fetch URLs.

## Validation and incremental loading

- All 22 source headers are required in their documented order. Dates become SQL
  DATE values; measures must be signed 32-bit integers. Missing, malformed and
  overflow values are quarantined with reasons rather than filled.
- `(settlement_date, settlement_period)` is the database primary key. Valid modern
  GB period bounds are 1–48 normally, 1–46 on the final Sunday of March and 1–50 on
  the final Sunday of October. Partial batches are allowed. No timestamps or
  missing observations are manufactured.
- Negative interconnector, transfer and pumping values remain valid. Physical
  anomaly thresholds are outside v1's validation contract.
- All occurrences of a duplicated key within one input are quarantined, avoiding
  arbitrary winners. Across batches, new keys insert, changed canonical hashes
  update and unchanged hashes skip. All source columns are retained.
- Valid records load in one transaction. A database failure rolls back that
  batch's writes. Raw snapshots, source checksums, source-row positions and JSON
  run reports preserve provenance. Unchanged rows retain their prior write metadata.

Exit codes: **0** successful load; **2** valid subset committed with rejected rows;
**1** failure. Inspect `artifacts/runs/<run_id>/summary.json` and `rejected.json`
(the latter is written after source validation). Structured JSON is also logged.

## SQL analysis

[sql/analysis_queries.sql](sql/analysis_queries.sql) provides monthly demand and
renewable means, settlement-period profiles and daily peaks. Open a generated
SQLite database in DB Browser for SQLite, or execute the queries through Python's
built-in `sqlite3` module. The stable interface is the `energy_records` table.

Captured full-year outputs: [monthly](evidence/monthly.csv),
[period profile](evidence/period_profile.csv) and [daily](evidence/daily.csv).
Average national demand was **26,286.76 MW** and peak demand **45,202 MW**.
Embedded wind/solar are estimated embedded output, not total GB generation.
Settlement-period indices are not universal fixed local/UTC time labels on clock
change dates; periods 49–50 have much smaller sample sizes.

For the existing overlap/quarantine demonstration, first load the complete CSV into
`gridflow.db` using the default database URL, then run:

```powershell
.\.venv\Scripts\python.exe -m gridflow data/raw/demanddata_2024.csv
.\.venv\Scripts\python.exe scripts/demonstrate.py
```

The script uses a separate disposable `artifacts/demo/overlap.db`, derives four rows
from the official data, changes one ND value by +1 MW to exercise updates and
injects one invalid value to exercise quarantine. These are controlled test cases,
not claims of official corrections. It regenerates analytical evidence files.

## Configuration

Default connection: `sqlite:///gridflow.db`. `--database-url` overrides the
`DATABASE_URL` environment variable. Parent directories for SQLite files must
exist. [.env.example](.env.example) documents configuration; it is not auto-loaded.

Optional PostgreSQL setup for an existing database:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[postgres]"
$env:DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@localhost:5432/gridflow"
.\.venv\Scripts\python.exe -m gridflow tests/fixtures/sample.csv
Remove-Item Env:DATABASE_URL
```

Native SQLAlchemy SQLite/PostgreSQL upserts are implemented. **PostgreSQL has not
been integration-tested.** Keep credentials out of Git. V1 assumes a single writer
and compares existing annual-table hashes in memory. It does not enforce source
revision ordering: loading an older changed batch can overwrite newer values.
Raw sources are retained, but there is no append-only row revision table.

## Tests and continuous integration

The existing tests cover parsing, signed values, malformed rows/headers,
clock-change bounds, duplicates, primary-key enforcement, rerun idempotency,
incremental changes, transaction rollback, error reports and SQL aggregates.
[Captured local test output](evidence/final-pytest.txt) records 21 passing tests.

[GitHub Actions workflow](.github/workflows/ci.yml) installs the package, runs pytest,
and ingests/reruns the fixture without secrets or a network dataset download. It
runs on pushes, pull requests and manual dispatch. Remote results must be read
from the Actions tab. This static 2024 dataset is not represented as a live feed.

## Repository contents

- `src/gridflow/`: CLI, validation, schema and transactional loader.
- `sql/`: analytical queries.
- `tests/`: pytest suite and four-row real-data fixture.
- `scripts/demonstrate.py`: reproducible controlled overlap/quarantine demo.
- `docs/`: [architecture](docs/architecture.md), [data dictionary](docs/data_dictionary.md)
  and [verification](docs/verification.md).
- `evidence/`: compact source inspection, captured local test result and aggregates.

Original Power BI assets, full datasets, databases, runtime archives and personal
working notes are excluded. The architecture documents a future read-only SQL
interface; an AI application is outside this project's implemented scope.
