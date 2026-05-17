from pathlib import Path
import sys

import psycopg
import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from db_config import DatabaseConfig


@pytest.fixture(scope="module")
def db_connection():
    try:
        config = DatabaseConfig.from_env()
        conn = psycopg.connect(**config.to_psycopg_kwargs())
    except Exception as exc:
        pytest.skip(f"PostgreSQL kapcsolat nem elérhető a delta energia teszthez: {exc}")

    try:
        yield conn
    finally:
        conn.close()


def test_negative_cumulative_delta_falls_back_to_power_based_estimate(db_connection):
    sql = """
    WITH energy_measurement(ts, machine_id, power_kw, energy_kwh_cumulative, sample_interval_sec) AS (
        VALUES
            (
                TIMESTAMPTZ '2025-01-01 10:00:00+00',
                1,
                6.0,
                100.0,
                60
            ),
            (
                TIMESTAMPTZ '2025-01-01 10:01:00+00',
                1,
                6.0,
                99.0,
                60
            )
    ),
    energy_base AS (
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
        ts,
        CASE
            WHEN energy_kwh_cumulative IS NOT NULL
                 AND prev_energy_kwh IS NOT NULL
                 AND energy_kwh_cumulative >= prev_energy_kwh
            THEN energy_kwh_cumulative - prev_energy_kwh

            WHEN sample_interval_sec IS NOT NULL
                 AND sample_interval_sec > 0
                 AND power_kw IS NOT NULL
            THEN power_kw * (sample_interval_sec / 3600.0)

            ELSE NULL
        END AS delta_energy_kwh
    FROM energy_base
    ORDER BY ts;
    """

    with db_connection.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    # első sorban nincs előző érték, ezért fallback: 6 kW * 60 sec / 3600 = 0.1 kWh
    assert float(rows[0][1]) == pytest.approx(0.1)

    # második sorban a kumulált energia csökkent (100 -> 99),
    # ezért nem negatív deltát használunk, hanem ugyanúgy fallbackot
    assert float(rows[1][1]) == pytest.approx(0.1)