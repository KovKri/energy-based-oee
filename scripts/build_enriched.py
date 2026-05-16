from pathlib import Path

import psycopg

from db_config import DatabaseConfig


BASE_DIR = Path(__file__).resolve().parent.parent


def main() -> None:
    config = DatabaseConfig.from_env()

    print("Build enriched layer started.")
    print(f"Project base directory: {BASE_DIR}")
    print(f"Connecting to database: {config.dbname} on {config.host}:{config.port}")

    truncate_energy_enriched_sql = "TRUNCATE TABLE energy_enriched;"
    truncate_cycle_summary_sql = "TRUNCATE TABLE cycle_energy_summary;"

    insert_energy_enriched_sql = """
    INSERT INTO energy_enriched (
        ts,
        machine_id,
        power_kw,
        delta_energy_kwh,
        detailed_state_code,
        state_tag,
        cycle_id
    )
    WITH energy_base AS (
        SELECT
            e.ts,
            e.machine_id,
            e.power_kw,
            e.energy_kwh_cumulative,
            e.sample_interval_sec,
            LAG(e.energy_kwh_cumulative) OVER (
                PARTITION BY e.machine_id
                ORDER BY e.ts
            ) AS prev_energy_kwh
        FROM energy_measurement e
    )
    SELECT
        eb.ts,
        eb.machine_id,
        eb.power_kw,
        CASE
            WHEN eb.energy_kwh_cumulative IS NOT NULL
                 AND eb.prev_energy_kwh IS NOT NULL
            THEN eb.energy_kwh_cumulative - eb.prev_energy_kwh
            WHEN eb.sample_interval_sec IS NOT NULL
            THEN eb.power_kw * (eb.sample_interval_sec / 3600.0)
            ELSE NULL
        END AS delta_energy_kwh,
        mse.detailed_state_code,
        mse.state_tag,
        ce.cycle_id
    FROM energy_base eb
    LEFT JOIN LATERAL (
        SELECT
            m.detailed_state_code,
            m.state_tag
        FROM machine_state_event m
        WHERE m.machine_id = eb.machine_id
          AND m.ts <= eb.ts
        ORDER BY m.ts DESC
        LIMIT 1
    ) mse ON TRUE
    LEFT JOIN cycle_event ce
        ON ce.machine_id = eb.machine_id
       AND eb.ts >= ce.cycle_start_ts
       AND eb.ts < ce.cycle_end_ts
    ORDER BY eb.machine_id, eb.ts;
    """

    insert_cycle_summary_sql = """
    INSERT INTO cycle_energy_summary (
        cycle_id,
        machine_id,
        operation_id,
        cycle_start_ts,
        cycle_end_ts,
        cycle_energy_kwh,
        part_result
    )
    SELECT
        ce.cycle_id,
        ce.machine_id,
        ce.operation_id,
        ce.cycle_start_ts,
        ce.cycle_end_ts,
        COALESCE(SUM(ee.delta_energy_kwh), 0) AS cycle_energy_kwh,
        ce.part_result
    FROM cycle_event ce
    LEFT JOIN energy_enriched ee
        ON ee.machine_id = ce.machine_id
       AND ee.ts >= ce.cycle_start_ts
       AND ee.ts < ce.cycle_end_ts
    GROUP BY
        ce.cycle_id,
        ce.machine_id,
        ce.operation_id,
        ce.cycle_start_ts,
        ce.cycle_end_ts,
        ce.part_result
    ORDER BY ce.cycle_start_ts;
    """

    with psycopg.connect(**config.to_psycopg_kwargs()) as conn:
        with conn.cursor() as cur:
            cur.execute(truncate_cycle_summary_sql)
            cur.execute(truncate_energy_enriched_sql)

            cur.execute(insert_energy_enriched_sql)
            cur.execute(insert_cycle_summary_sql)

            cur.execute("SELECT COUNT(*) FROM energy_enriched;")
            energy_enriched_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM cycle_energy_summary;")
            cycle_summary_count = cur.fetchone()[0]

            cur.execute(
                """
                SELECT
                    ts,
                    machine_id,
                    power_kw,
                    delta_energy_kwh,
                    detailed_state_code,
                    state_tag,
                    cycle_id
                FROM energy_enriched
                ORDER BY ts
                LIMIT 10;
                """
            )
            energy_preview = cur.fetchall()

            cur.execute(
                """
                SELECT
                    cycle_id,
                    machine_id,
                    operation_id,
                    cycle_start_ts,
                    cycle_end_ts,
                    cycle_energy_kwh,
                    part_result
                FROM cycle_energy_summary
                ORDER BY cycle_start_ts
                LIMIT 10;
                """
            )
            cycle_preview = cur.fetchall()

        conn.commit()

    print(f"energy_enriched rows: {energy_enriched_count}")
    print(f"cycle_energy_summary rows: {cycle_summary_count}")

    print("\nenergy_enriched preview:")
    for row in energy_preview:
        print(row)

    print("\ncycle_energy_summary preview:")
    for row in cycle_preview:
        print(row)


if __name__ == "__main__":
    main()