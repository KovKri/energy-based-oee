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
        pytest.skip(f"PostgreSQL kapcsolat nem elérhető a ciklushatár teszthez: {exc}")

    try:
        yield conn
    finally:
        conn.close()


def test_cycle_boundary_uses_half_open_interval(db_connection):
    sql = """
    WITH cycle_event(machine_id, cycle_id, cycle_start_ts, cycle_end_ts) AS (
        VALUES
            (
                1,
                100,
                TIMESTAMPTZ '2025-01-01 10:00:00+00',
                TIMESTAMPTZ '2025-01-01 10:05:00+00'
            ),
            (
                1,
                101,
                TIMESTAMPTZ '2025-01-01 10:05:00+00',
                TIMESTAMPTZ '2025-01-01 10:10:00+00'
            )
    ),
    samples(sample_ts) AS (
        VALUES
            (TIMESTAMPTZ '2025-01-01 10:00:00+00'),
            (TIMESTAMPTZ '2025-01-01 10:04:59+00'),
            (TIMESTAMPTZ '2025-01-01 10:05:00+00'),
            (TIMESTAMPTZ '2025-01-01 10:09:59+00'),
            (TIMESTAMPTZ '2025-01-01 10:10:00+00')
    )
    SELECT
        sample_ts,
        cycle_id
    FROM samples s
    LEFT JOIN cycle_event ce
        ON ce.machine_id = 1
       AND s.sample_ts >= ce.cycle_start_ts
       AND s.sample_ts < ce.cycle_end_ts
    ORDER BY sample_ts;
    """

    with db_connection.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    result = {row[0].isoformat(): row[1] for row in rows}

    assert result["2025-01-01T10:00:00+00:00"] == 100
    assert result["2025-01-01T10:04:59+00:00"] == 100

    # A ciklus vége már ne az első ciklushoz tartozzon,
    # hanem pontosan a következőhöz.
    assert result["2025-01-01T10:05:00+00:00"] == 101
    assert result["2025-01-01T10:09:59+00:00"] == 101

    # A második ciklus végpontja már egyikhez se tartozzon.
    assert result["2025-01-01T10:10:00+00:00"] is None