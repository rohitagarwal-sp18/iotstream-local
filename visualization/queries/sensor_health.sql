-- Sensor health dashboard — last 1 hour, worst sensors first
-- Shows active/degraded/offline event breakdown and overall health percentage

SELECT
    sensor_id,
    location,
    SUM(active_count)                                          AS active_count,
    SUM(degraded_count)                                        AS degraded_count,
    SUM(offline_count)                                         AS offline_count,
    SUM(event_count)                                           AS total_event_count,
    ROUND(SUM(active_count) * 100.0 / NULLIF(SUM(event_count), 0), 2) AS health_pct
FROM iotstream.gold.sensor_metrics_1min
WHERE window_start >= NOW() - INTERVAL '1' HOUR
GROUP BY
    sensor_id,
    location
ORDER BY health_pct ASC;
