import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


def main() -> None:
    load_dotenv()

    db_name = os.getenv("POSTGRES_DB")
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_host = "localhost"

    print("KPI validation started.")
    print(f"Project base directory: {BASE_DIR}")
    print(f"Connecting to database: {db_name} on {db_host}:{db_port}")

    sql = """
    WITH energy_stats AS (
        SELECT
            COALESCE(SUM(delta_energy_kwh), 0) AS energy_total_kwh,
            COALESCE(SUM(CASE WHEN state_tag = 'termelő' THEN delta_energy_kwh ELSE 0 END), 0) AS energy_productive_kwh,
            COALESCE(SUM(CASE WHEN state_tag = 'nem termelő' THEN delta_energy_kwh ELSE 0 END), 0) AS energy_non_productive_kwh,
            COALESCE(SUM(CASE WHEN state_tag = 'nem termelő és áll' THEN delta_energy_kwh ELSE 0 END), 0) AS energy_non_productive_stop_kwh
        FROM energy_enriched
    ),
    cycle_stats AS (
        SELECT
            COUNT(*) AS total_parts,
            COUNT(*) FILTER (WHERE part_result = 'good') AS good_parts,
            COUNT(*) FILTER (WHERE part_result = 'scrap') AS scrap_parts,
            COALESCE(SUM(cycle_energy_kwh), 0) AS total_cycle_energy_kwh,
            COALESCE(SUM(cycle_energy_kwh) FILTER (WHERE part_result = 'good'), 0) AS good_cycle_energy_kwh,
            COALESCE(SUM(cycle_energy_kwh) FILTER (WHERE part_result = 'scrap'), 0) AS scrap_cycle_energy_kwh,
            COALESCE(STDDEV_POP(cycle_energy_kwh), 0) AS cycle_energy_stddev_kwh
        FROM cycle_energy_summary
    )
    SELECT
        es.energy_total_kwh,
        es.energy_productive_kwh,
        es.energy_non_productive_kwh,
        es.energy_non_productive_stop_kwh,
        CASE
            WHEN es.energy_total_kwh > 0
            THEN es.energy_productive_kwh / es.energy_total_kwh
            ELSE 0
        END AS productive_energy_ratio,
        CASE
            WHEN es.energy_total_kwh > 0
            THEN (es.energy_non_productive_kwh + es.energy_non_productive_stop_kwh) / es.energy_total_kwh
            ELSE 0
        END AS non_productive_energy_ratio,
        cs.total_parts,
        cs.good_parts,
        cs.scrap_parts,
        CASE
            WHEN cs.total_parts > 0
            THEN cs.total_cycle_energy_kwh / cs.total_parts
            ELSE 0
        END AS energy_per_part_kwh,
        CASE
            WHEN cs.good_parts > 0
            THEN cs.good_cycle_energy_kwh / cs.good_parts
            ELSE 0
        END AS cycle_energy_per_good_part_kwh,
        CASE
            WHEN cs.scrap_parts > 0
            THEN cs.scrap_cycle_energy_kwh / cs.scrap_parts
            ELSE 0
        END AS energy_per_scrap_part_kwh,
        cs.cycle_energy_stddev_kwh,
        CASE
            WHEN cs.good_parts > 0
            THEN es.energy_total_kwh / cs.good_parts
            ELSE 0
        END AS system_energy_per_good_part_kwh
    FROM energy_stats es
    CROSS JOIN cycle_stats cs;
    """

    with psycopg.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()

    columns = [
        "energy_total_kwh",
        "energy_productive_kwh",
        "energy_non_productive_kwh",
        "energy_non_productive_stop_kwh",
        "productive_energy_ratio",
        "non_productive_energy_ratio",
        "total_parts",
        "good_parts",
        "scrap_parts",
        "energy_per_part_kwh",
        "cycle_energy_per_good_part_kwh",
        "energy_per_scrap_part_kwh",
        "cycle_energy_stddev_kwh",
        "system_energy_per_good_part_kwh",
    ]

    print("\nComputed KPI values:")
    for name, value in zip(columns, row):
        print(f"{name}: {value}")


if __name__ == "__main__":
    main()