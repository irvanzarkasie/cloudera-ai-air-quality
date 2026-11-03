-- Reference: last 7 days, worst kecamatan (read-only, WITH clauses only)

-- Top 10 worst kecamatan by mean ISPU (last 7 calendar dates in table)
WITH date_bounds AS (
  SELECT MAX(observation_date) AS max_d
  FROM id_workshop.jakarta_air_daily
),
last7 AS (
  SELECT DISTINCT observation_date
  FROM id_workshop.jakarta_air_daily d, date_bounds b
  WHERE d.observation_date > CAST(
    DATE_SUB(CAST(b.max_d AS TIMESTAMP), 6) AS STRING
  )
),
daily_kecamatan AS (
  SELECT
    d.observation_date,
    d.kecamatan,
    AVG(d.ispu) AS avg_ispu,
    COUNT(*) AS station_count
  FROM id_workshop.jakarta_air_daily d
  INNER JOIN last7 l ON d.observation_date = l.observation_date
  WHERE d.kecamatan IS NOT NULL AND TRIM(d.kecamatan) != ''
  GROUP BY d.observation_date, d.kecamatan
)
SELECT
  kecamatan,
  ROUND(AVG(avg_ispu), 2) AS mean_ispu_7d,
  SUM(station_count) AS station_day_samples
FROM daily_kecamatan
GROUP BY kecamatan
ORDER BY mean_ispu_7d DESC
LIMIT 10;
