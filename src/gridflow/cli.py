"""Local-file ingestion CLI with raw retention and per-run JSON evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from time import perf_counter
from uuid import uuid4
from .load import load_records
from .validate import validate_file


def run(source, database_url, artifacts="artifacts"):
    start = perf_counter()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex[:8]
    directory = Path(artifacts) / "runs" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    report = {"run_id": run_id, "started_at": datetime.now(timezone.utc).isoformat(),
              "source_file": Path(source).name, "source_sha256": None,
              "input_rows": 0, "inserted": 0, "updated": 0, "skipped": 0, "rejected": 0}
    exit_code = 1
    try:
        checksum = hashlib.sha256(Path(source).read_bytes()).hexdigest()
        report["source_sha256"] = checksum
        raw = Path(artifacts) / "raw" / (checksum + ".csv")
        raw.parent.mkdir(parents=True, exist_ok=True)
        if not raw.exists():
            shutil.copyfile(source, raw)
        # Validate the retained snapshot, never a subsequently changed input path.
        rows, rejected, total = validate_file(raw, checksum)
        report.update(input_rows=total, rejected=len(rejected), raw_file=str(raw))
        (directory / "rejected.json").write_text(json.dumps(rejected, indent=2), encoding="utf-8")
        report.update(load_records(database_url, rows))
        report["status"] = "completed_with_rejections" if rejected else "completed"
        exit_code = 2 if rejected else 0
    except Exception as error:
        report["status"] = "failed"
        # Database exception strings can contain credentials or source data.
        report["error"] = str(error) if isinstance(error, (ValueError, FileNotFoundError)) else type(error).__name__
    report["duration_seconds"] = round(perf_counter() - start, 6)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["exit_code"] = exit_code
    report["report_file"] = str(directory / "summary.json")
    (directory / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"event": "ingest_complete", **report}), file=sys.stderr)
    print(f"{report['status']}: inserted={report['inserted']} updated={report['updated']} "
          f"skipped={report['skipped']} rejected={report['rejected']}; report={report['report_file']}")
    return report


def main():
    parser = argparse.ArgumentParser(description="Ingest official NESO demand CSV into SQLite/PostgreSQL")
    parser.add_argument("source", type=Path)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", "sqlite:///gridflow.db"))
    parser.add_argument("--artifacts", default="artifacts")
    args = parser.parse_args()
    return run(args.source, args.database_url, args.artifacts)["exit_code"]
