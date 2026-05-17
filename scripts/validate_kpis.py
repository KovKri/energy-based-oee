from decimal import Decimal
from pathlib import Path
import logging

import psycopg

from db_config import DatabaseConfig


BASE_DIR = Path(__file__).resolve().parent.parent
LOGGER = logging.getLogger(__name__)
TOLERANCE = Decimal("0.000001")


class KpiValidationError(AssertionError):
    """A számított KPI-ok belső konzisztencia-ellenőrzése elbukott."""


def fetch_kpis(conn: psycopg.Connection) -> dict[str, object]:
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

    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    if row is None:
        raise KpiValidationError("A KPI lekérdezés nem adott vissza eredményt.")

    return dict(zip(columns, row))


def assert_kpi_invariants(kpis: dict[str, object]) -> None:
    productive_ratio = Decimal(str(kpis["productive_energy_ratio"]))
    non_productive_ratio = Decimal(str(kpis["non_productive_energy_ratio"]))

    if not Decimal("0") <= productive_ratio <= Decimal("1"):
        raise KpiValidationError(
            f"productive_energy_ratio kívül van [0,1] tartományon: {productive_ratio}"
        )

    if not Decimal("0") <= non_productive_ratio <= Decimal("1"):
        raise KpiValidationError(
            f"non_productive_energy_ratio kívül van [0,1] tartományon: {non_productive_ratio}"
        )

    energy_total = Decimal(str(kpis["energy_total_kwh"]))
    energy_productive = Decimal(str(kpis["energy_productive_kwh"]))
    energy_non_productive = Decimal(str(kpis["energy_non_productive_kwh"]))
    energy_non_productive_stop = Decimal(str(kpis["energy_non_productive_stop_kwh"]))

    component_sum = (
        energy_productive
        + energy_non_productive
        + energy_non_productive_stop
    )

    if abs(component_sum - energy_total) > TOLERANCE:
        raise KpiValidationError(
            "Az energia komponensek nem adják ki az összes energiát: "
            f"{component_sum} vs {energy_total}"
        )

    total_parts = int(kpis["total_parts"])
    good_parts = int(kpis["good_parts"])
    scrap_parts = int(kpis["scrap_parts"])

    if good_parts + scrap_parts != total_parts:
        raise KpiValidationError(
            f"good_parts + scrap_parts != total_parts: "
            f"{good_parts} + {scrap_parts} != {total_parts}"
        )

    for metric_name in [
        "energy_total_kwh",
        "energy_productive_kwh",
        "energy_non_productive_kwh",
        "energy_non_productive_stop_kwh",
        "energy_per_part_kwh",
        "cycle_energy_per_good_part_kwh",
        "energy_per_scrap_part_kwh",
        "cycle_energy_stddev_kwh",
        "system_energy_per_good_part_kwh",
    ]:
        metric_value = Decimal(str(kpis[metric_name]))
        if metric_value < 0:
            raise KpiValidationError(
                f"{metric_name} nem lehet negatív: {metric_value}"
            )

    LOGGER.info("Minden KPI invariáns érvényes.")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config = DatabaseConfig.from_env()

    print("KPI validation started.")
    print(f"Project base directory: {BASE_DIR}")
    print(f"Connecting to database: {config.dbname} on {config.host}:{config.port}")

    with psycopg.connect(**config.to_psycopg_kwargs()) as conn:
        kpis = fetch_kpis(conn)

    assert_kpi_invariants(kpis)

    print("\nKPI validation passed.")
    print("\nComputed KPI values:")
    for name, value in kpis.items():
        print(f"{name}: {value}")


if __name__ == "__main__":
    main()