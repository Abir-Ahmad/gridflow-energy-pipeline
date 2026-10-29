# Data dictionary

Schema owner: `src/gridflow/models.py`; table: `energy_records`. All source fields are retained.

| Official column | SQL column | Type / unit |
| --- | --- | --- |
| SETTLEMENT_DATE | settlement_date | DATE / settlement calendar date |
| SETTLEMENT_PERIOD | settlement_period | INTEGER / period index |
| ND | national_demand_mw | INTEGER / MW |
| TSD | transmission_demand_mw | INTEGER / MW |
| ENGLAND_WALES_DEMAND | england_wales_demand | INTEGER / MW |
| EMBEDDED_WIND_GENERATION | embedded_wind_generation | INTEGER / MW |
| EMBEDDED_WIND_CAPACITY | embedded_wind_capacity | INTEGER / MW |
| EMBEDDED_SOLAR_GENERATION | embedded_solar_generation | INTEGER / MW |
| EMBEDDED_SOLAR_CAPACITY | embedded_solar_capacity | INTEGER / MW |
| NON_BM_STOR | non_bm_stor | INTEGER / MW |
| PUMP_STORAGE_PUMPING | pump_storage_pumping | INTEGER / MW |
| SCOTTISH_TRANSFER | scottish_transfer | INTEGER / MW |
| IFA_FLOW | ifa_flow | INTEGER / MW |
| IFA2_FLOW | ifa2_flow | INTEGER / MW |
| BRITNED_FLOW | britned_flow | INTEGER / MW |
| MOYLE_FLOW | moyle_flow | INTEGER / MW |
| EAST_WEST_FLOW | east_west_flow | INTEGER / MW |
| NEMO_FLOW | nemo_flow | INTEGER / MW |
| NSL_FLOW | nsl_flow | INTEGER / MW |
| ELECLINK_FLOW | eleclink_flow | INTEGER / MW |
| VIKING_FLOW | viking_flow | INTEGER / MW |
| GREENLINK_FLOW | greenlink_flow | INTEGER / MW |

All columns are NOT NULL. The first two columns form the composite primary key.
No fixed 48-row daily constraint is applied. Source 31 March 2024 has 46 periods;
27 October 2024 has 50. No timestamps are fabricated.

| Provenance column | Meaning |
| --- | --- |
| record_hash | SHA-256 of canonical normalized values, including key |
| source_sha256 | SHA-256 of retained CSV responsible for last row write |
| source_line | 1-based CSV record position including header; source has no multiline fields |
| raw_record | JSON object containing all original source strings |

ND is national demand excluding station load, pumping and exports; TSD additionally
accounts for those requirements. Embedded wind/solar are NESO estimates of generation
within distribution networks and their installed capacity, not total GB renewable output.
NON_BM_STOR is non-Balancing Mechanism short-term operating reserve; pumping is
hydro storage pumping demand. Scottish transfer can flow in either direction. Negative
interconnector values indicate exports, positive imports. Signs are preserved.

Units and definitions follow the [official NESO metadata](https://www.neso.energy/data-portal/historic-demand-data/historic_demand_data_2024).
Raw JSON preserves original lexical representation; comparison hashes normalize dates
and integer formatting. Files remain preserved even when their normalized rows skip.
