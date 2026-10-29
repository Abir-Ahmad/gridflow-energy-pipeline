"""SQLAlchemy owns the portable relational schema."""
from sqlalchemy import MetaData, Table, Column, Date, Integer, Text, String

HEADERS = "SETTLEMENT_DATE SETTLEMENT_PERIOD ND TSD ENGLAND_WALES_DEMAND EMBEDDED_WIND_GENERATION EMBEDDED_WIND_CAPACITY EMBEDDED_SOLAR_GENERATION EMBEDDED_SOLAR_CAPACITY NON_BM_STOR PUMP_STORAGE_PUMPING SCOTTISH_TRANSFER IFA_FLOW IFA2_FLOW BRITNED_FLOW MOYLE_FLOW EAST_WEST_FLOW NEMO_FLOW NSL_FLOW ELECLINK_FLOW VIKING_FLOW GREENLINK_FLOW".split()
NAMES = {h: h.lower() for h in HEADERS}
NAMES.update(ND="national_demand_mw", TSD="transmission_demand_mw")
metadata = MetaData()
energy = Table(
    "energy_records", metadata,
    Column("settlement_date", Date, primary_key=True),
    Column("settlement_period", Integer, primary_key=True),
    *[Column(NAMES[h], Integer, nullable=False) for h in HEADERS[2:]],
    Column("record_hash", String(64), nullable=False),
    Column("source_sha256", String(64), nullable=False),
    Column("source_line", Integer, nullable=False),
    Column("raw_record", Text, nullable=False),
)
