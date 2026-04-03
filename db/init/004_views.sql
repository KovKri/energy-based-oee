CREATE OR REPLACE VIEW state_energy_summary_hourly AS
SELECT
    time_bucket('1 hour', ts) AS bucket_start,
    machine_id,
    COALESCE(SUM(delta_energy_kwh), 0) AS energy_total_kwh,
    COALESCE(SUM(CASE WHEN state_tag = 'termelő' THEN delta_energy_kwh ELSE 0 END), 0) AS energy_productive_kwh,
    COALESCE(SUM(CASE WHEN state_tag = 'nem termelő' THEN delta_energy_kwh ELSE 0 END), 0) AS energy_non_productive_kwh,
    COALESCE(SUM(CASE WHEN state_tag = 'nem termelő és áll' THEN delta_energy_kwh ELSE 0 END), 0) AS energy_non_productive_stop_kwh,
    CASE
        WHEN COALESCE(SUM(delta_energy_kwh), 0) > 0
        THEN COALESCE(SUM(CASE WHEN state_tag = 'termelő' THEN delta_energy_kwh ELSE 0 END), 0)
             / SUM(delta_energy_kwh)
        ELSE 0
    END AS productive_energy_ratio,
    CASE
        WHEN COALESCE(SUM(delta_energy_kwh), 0) > 0
        THEN (
            COALESCE(SUM(CASE WHEN state_tag = 'nem termelő' THEN delta_energy_kwh ELSE 0 END), 0)
            + COALESCE(SUM(CASE WHEN state_tag = 'nem termelő és áll' THEN delta_energy_kwh ELSE 0 END), 0)
        ) / SUM(delta_energy_kwh)
        ELSE 0
    END AS non_productive_energy_ratio
FROM energy_enriched
GROUP BY
    time_bucket('1 hour', ts),
    machine_id
ORDER BY
    bucket_start,
    machine_id;


CREATE OR REPLACE VIEW oee_energy_summary_hourly AS
WITH machines AS (
    SELECT machine_id FROM machine
    UNION
    SELECT machine_id FROM energy_measurement
    UNION
    SELECT machine_id FROM machine_state_event
    UNION
    SELECT machine_id FROM cycle_event
),
machine_time_bounds AS (
    SELECT
        m.machine_id,
        GREATEST(
            COALESCE(
                (
                    SELECT MAX(
                        e.ts + COALESCE((e.sample_interval_sec::text || ' seconds')::interval, interval '0 seconds')
                    )
                    FROM energy_measurement e
                    WHERE e.machine_id = m.machine_id
                ),
                TIMESTAMPTZ '1970-01-01 00:00:00+00'
            ),
            COALESCE(
                (
                    SELECT MAX(mse.ts)
                    FROM machine_state_event mse
                    WHERE mse.machine_id = m.machine_id
                ),
                TIMESTAMPTZ '1970-01-01 00:00:00+00'
            ),
            COALESCE(
                (
                    SELECT MAX(ce.cycle_end_ts)
                    FROM cycle_event ce
                    WHERE ce.machine_id = m.machine_id
                ),
                TIMESTAMPTZ '1970-01-01 00:00:00+00'
            )
        ) AS max_bound_ts
    FROM machines m
),
raw_state_intervals AS (
    SELECT
        mse.machine_id,
        mse.ts AS start_ts,
        COALESCE(
            LEAD(mse.ts) OVER (
                PARTITION BY mse.machine_id
                ORDER BY mse.ts
            ),
            mtb.max_bound_ts
        ) AS end_ts,
        mse.detailed_state_code,
        mse.state_tag,
        mse.reason_code,
        mse.is_planned_stop,
        mse.idle_reason
    FROM machine_state_event mse
    JOIN machine_time_bounds mtb
        ON mtb.machine_id = mse.machine_id
),
state_intervals AS (
    SELECT *
    FROM raw_state_intervals
    WHERE end_ts > start_ts
),
state_interval_bucketed AS (
    SELECT
        si.machine_id,
        gs.bucket_start,
        GREATEST(si.start_ts, gs.bucket_start) AS interval_start,
        LEAST(si.end_ts, gs.bucket_start + interval '1 hour') AS interval_end,
        si.detailed_state_code,
        si.state_tag,
        si.is_planned_stop,
        si.idle_reason
    FROM state_intervals si
    CROSS JOIN LATERAL generate_series(
        date_trunc('hour', si.start_ts),
        date_trunc('hour', si.end_ts - interval '1 microsecond'),
        interval '1 hour'
    ) AS gs(bucket_start)
),
state_time_hourly AS (
    SELECT
        bucket_start,
        machine_id,
        SUM(
            CASE
                WHEN NOT is_planned_stop
                THEN EXTRACT(EPOCH FROM (interval_end - interval_start))
                ELSE 0
            END
        ) AS planned_time_sec,
        SUM(
            CASE
                WHEN NOT is_planned_stop
                     AND (
                        detailed_state_code = 'FAILURE'
                        OR state_tag = 'nem termelő és áll'
                        OR (
                            detailed_state_code = 'IDLE'
                            AND COALESCE(idle_reason, '') = 'simple_waiting'
                        )
                     )
                THEN EXTRACT(EPOCH FROM (interval_end - interval_start))
                ELSE 0
            END
        ) AS availability_loss_sec
    FROM state_interval_bucketed
    WHERE interval_end > interval_start
    GROUP BY
        bucket_start,
        machine_id
),
cycle_stats_hourly AS (
    SELECT
        time_bucket('1 hour', ce.cycle_start_ts) AS bucket_start,
        ce.machine_id,
        COUNT(*) AS total_parts,
        COUNT(*) FILTER (WHERE ce.part_result = 'good') AS good_parts,
        COUNT(*) FILTER (WHERE ce.part_result = 'scrap') AS scrap_parts,
        COALESCE(SUM(o.ideal_cycle_time_sec), 0) AS ideal_cycle_time_total_sec,
        COALESCE(SUM(ce.actual_cycle_time_sec), 0) AS actual_cycle_time_total_sec,
        COALESCE(SUM(ces.cycle_energy_kwh), 0) AS total_cycle_energy_kwh,
        COALESCE(SUM(ces.cycle_energy_kwh) FILTER (WHERE ce.part_result = 'good'), 0) AS good_cycle_energy_kwh,
        COALESCE(SUM(ces.cycle_energy_kwh) FILTER (WHERE ce.part_result = 'scrap'), 0) AS scrap_cycle_energy_kwh
    FROM cycle_event ce
    JOIN operation o
        ON o.operation_id = ce.operation_id
    LEFT JOIN cycle_energy_summary ces
        ON ces.cycle_id = ce.cycle_id
    GROUP BY
        time_bucket('1 hour', ce.cycle_start_ts),
        ce.machine_id
),
all_buckets AS (
    SELECT bucket_start, machine_id FROM state_energy_summary_hourly
    UNION
    SELECT bucket_start, machine_id FROM state_time_hourly
    UNION
    SELECT bucket_start, machine_id FROM cycle_stats_hourly
)
SELECT
    ab.bucket_start,
    ab.machine_id,
    CASE
        WHEN COALESCE(sth.planned_time_sec, 0) > 0
        THEN (sth.planned_time_sec - COALESCE(sth.availability_loss_sec, 0)) / sth.planned_time_sec
        ELSE 0
    END AS availability,
    CASE
        WHEN COALESCE(csh.actual_cycle_time_total_sec, 0) > 0
        THEN csh.ideal_cycle_time_total_sec / csh.actual_cycle_time_total_sec
        ELSE 0
    END AS performance,
    CASE
        WHEN COALESCE(csh.total_parts, 0) > 0
        THEN csh.good_parts::numeric / csh.total_parts
        ELSE 0
    END AS quality,
    (
        CASE
            WHEN COALESCE(sth.planned_time_sec, 0) > 0
            THEN (sth.planned_time_sec - COALESCE(sth.availability_loss_sec, 0)) / sth.planned_time_sec
            ELSE 0
        END
        *
        CASE
            WHEN COALESCE(csh.actual_cycle_time_total_sec, 0) > 0
            THEN csh.ideal_cycle_time_total_sec / csh.actual_cycle_time_total_sec
            ELSE 0
        END
        *
        CASE
            WHEN COALESCE(csh.total_parts, 0) > 0
            THEN csh.good_parts::numeric / csh.total_parts
            ELSE 0
        END
    ) AS oee,
    COALESCE(seh.energy_total_kwh, 0) AS energy_total_kwh,
    CASE
        WHEN COALESCE(csh.total_parts, 0) > 0
        THEN csh.total_cycle_energy_kwh / csh.total_parts
        ELSE 0
    END AS energy_per_part_kwh,
    CASE
        WHEN COALESCE(csh.good_parts, 0) > 0
        THEN csh.good_cycle_energy_kwh / csh.good_parts
        ELSE 0
    END AS energy_per_good_part_kwh,
    CASE
        WHEN COALESCE(csh.good_parts, 0) > 0
        THEN csh.good_cycle_energy_kwh / csh.good_parts
        ELSE 0
    END AS cycle_energy_per_good_part_kwh,
    CASE
        WHEN COALESCE(csh.good_parts, 0) > 0
        THEN COALESCE(seh.energy_total_kwh, 0) / csh.good_parts
        ELSE 0
    END AS system_energy_per_good_part_kwh
FROM all_buckets ab
LEFT JOIN state_energy_summary_hourly seh
    ON seh.bucket_start = ab.bucket_start
   AND seh.machine_id = ab.machine_id
LEFT JOIN state_time_hourly sth
    ON sth.bucket_start = ab.bucket_start
   AND sth.machine_id = ab.machine_id
LEFT JOIN cycle_stats_hourly csh
    ON csh.bucket_start = ab.bucket_start
   AND csh.machine_id = ab.machine_id
ORDER BY
    ab.bucket_start,
    ab.machine_id;