-- Realtime sensor metrics — last 5 minutes
-- Use in Metabase as a question or dashboard card (auto-refresh recommended)

SELECT
    sensor_id,
    location,
    avg_temperature,
    avg_humidity,
    event_count,
    window_start
FROM iotstream.gold.sensor_metrics_1min
WHERE window_start >= NOW() - INTERVAL '5' MINUTE
ORDER BY window_start DESC;
