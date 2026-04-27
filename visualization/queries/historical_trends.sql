-- Historical trends — last 24 hours, 5-minute averages by location
-- Aggregates across all sensors at each location per window

SELECT
    window_start,
    location,
    ROUND(AVG(avg_temperature), 2) AS avg_temperature,
    ROUND(AVG(avg_humidity), 2)    AS avg_humidity
FROM iotstream.gold.sensor_metrics_1min
WHERE window_start >= NOW() - INTERVAL '24' HOUR
GROUP BY
    window_start,
    location
ORDER BY
    window_start,
    location;
