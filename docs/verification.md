# Verification record

The completed v1 was locally tested on 29 October 2026 before this public source
package was prepared. Python source, SQL, tests, fixture and package dependencies
were reused unchanged. Public packaging updates documentation and ignored-file
rules only; it does not rebuild the pipeline.

| Local verification | Recorded outcome |
| --- | --- |
| Official CSV | 22 columns, 17,568 records |
| Initial load | 17,568 inserted, 0 rejected |
| Identical-file rerun | 0 inserted, 0 updated, 17,568 skipped |
| Natural key count | 17,568 rows and 17,568 distinct keys |
| Controlled overlapping batch | 1 inserted, 1 updated, 2 skipped |
| Controlled invalid input | 1 rejected, 3 skipped, exit code 2 |
| Test suite | 21 passed, 0 failed (`python -m pytest -q`) |
| Transaction rollback | Mid-batch failure test confirms prior writes roll back |

The overlap demonstration modifies one official ND value by +1 MW in a separate
disposable database. This does not imply an official source correction.

Retained evidence: [source inspection](../evidence/source_inspection.json),
[local pytest output](../evidence/final-pytest.txt),
[monthly](../evidence/monthly.csv), [profile](../evidence/period_profile.csv),
[daily](../evidence/daily.csv). Large runtime archives and preloaded databases are
excluded. Reproduce the complete demonstration by downloading the official input,
loading it with the default database URL and running `scripts/demonstrate.py`.

PostgreSQL integration and execution on a Windows host remain unverified. GitHub
Actions status is separate from this historical local verification record; inspect
the repository's Actions tab for actual remote runs.
