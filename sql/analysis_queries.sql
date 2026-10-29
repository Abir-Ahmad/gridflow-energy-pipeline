-- 1. Monthly demand and embedded renewable generation, means and peaks in MW.
SELECT substr(CAST(settlement_date AS VARCHAR(10)), 1, 7) AS month,
       COUNT(*) AS periods,
       AVG(national_demand_mw) AS avg_demand_mw,
       MAX(national_demand_mw) AS peak_demand_mw,
       AVG(embedded_wind_generation) AS avg_embedded_wind_mw,
       AVG(embedded_solar_generation) AS avg_embedded_solar_mw
FROM energy_records
GROUP BY substr(CAST(settlement_date AS VARCHAR(10)), 1, 7)
ORDER BY month;

-- 2. Profile by settlement-period index, NOT a fixed local/UTC time label on DST days.
SELECT settlement_period, COUNT(*) AS observations,
       AVG(national_demand_mw) AS avg_demand_mw,
       AVG(embedded_wind_generation) AS avg_embedded_wind_mw,
       AVG(embedded_solar_generation) AS avg_embedded_solar_mw
FROM energy_records
GROUP BY settlement_period
ORDER BY settlement_period;

-- 3. Daily peaks and renewable means, with coverage visible.
SELECT settlement_date, COUNT(*) AS periods,
       MAX(national_demand_mw) AS peak_demand_mw,
       AVG(embedded_wind_generation) AS avg_embedded_wind_mw,
       AVG(embedded_solar_generation) AS avg_embedded_solar_mw
FROM energy_records
GROUP BY settlement_date
ORDER BY settlement_date;
