import csv
from pathlib import Path
import pytest
from gridflow.models import HEADERS

@pytest.fixture
def source_rows():
    with (Path(__file__).parent / "fixtures/sample.csv").open() as f:
        return list(csv.DictReader(f))

@pytest.fixture
def write_csv(tmp_path):
    def write(rows, headers=HEADERS, name="batch.csv"):
        path = tmp_path / name
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()
            w.writerows(rows)
        return path
    return write

@pytest.fixture
def database_url(tmp_path):
    return "sqlite:///" + str(tmp_path / "test.db")
