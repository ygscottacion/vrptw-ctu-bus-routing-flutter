-- BUG-VRPTW-01 post-deploy integrity monitor (Supabase/PostgreSQL).
-- Any returned row is a false-success candidate and should page the on-call
-- owner when it remains present for more than one monitoring interval.
SELECT
    r.id AS route_id,
    r.route_job_id,
    r.service_date,
    r.session_id,
    r.trip_type,
    COUNT(t.id) FILTER (WHERE t.status = 'assigned') AS passenger_count,
    COUNT(rs.id) AS route_stop_count
FROM routes AS r
LEFT JOIN tickets AS t ON t.route_id = r.id
LEFT JOIN route_stops AS rs ON rs.route_id = r.id
GROUP BY r.id, r.route_job_id, r.service_date, r.session_id, r.trip_type
HAVING COUNT(t.id) FILTER (WHERE t.status = 'assigned') > 0
   AND COUNT(rs.id) <= 1;

-- Recommended: run every five minutes with Supabase pg_cron or the existing
-- cron worker, export the result count as metric `vrptw_false_success_routes`,
-- and alert at > 0 for two consecutive runs. Include route_id and route_job_id
-- in the alert payload for immediate investigation.
