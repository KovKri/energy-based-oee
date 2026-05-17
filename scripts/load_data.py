from pathlib import Path
from typing import Any, Callable

import pandas as pd
import psycopg

from db_config import DatabaseConfig


BASE_DIR = Path(__file__).resolve().parent.parent
SEEDS_DIR = BASE_DIR / "db" / "seeds"

TABLE_LOAD_ORDER = [
    "machine",
    "operation",
    "state_mapping",
    "machine_state_event",
    "cycle_event",
    "energy_measurement",
]

TABLE_TRUNCATE_ORDER = [
    "energy_measurement",
    "cycle_event",
    "machine_state_event",
    "state_mapping",
    "operation",
    "machine",
]

TABLE_COLUMNS: dict[str, list[str]] = {
    "machine": [
        "machine_id",
        "machine_name",
        "manufacturer",
        "model",
        "machine_type",
    ],
    "operation": [
        "operation_id",
        "operation_name",
        "ideal_cycle_time_sec",
    ],
    "state_mapping": [
        "detailed_state_code",
        "detailed_state_name",
        "state_tag",
        "oee_loss_type",
    ],
    "machine_state_event": [
        "ts",
        "machine_id",
        "detailed_state_code",
        "state_tag",
        "reason_code",
        "is_planned_stop",
        "idle_reason",
    ],
    "cycle_event": [
        "cycle_id",
        "machine_id",
        "operation_id",
        "cycle_start_ts",
        "cycle_end_ts",
        "actual_cycle_time_sec",
        "part_result",
        "scrap_reason",
    ],
    "energy_measurement": [
        "ts",
        "machine_id",
        "power_kw",
        "energy_kwh_cumulative",
        "sample_interval_sec",
    ],
}


def parse_bool(value: object) -> bool:
    """Vegyes formátumú CSV-boolean -> Python bool."""
    if pd.isna(value):
        return False

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()

    if normalized in {"true", "1", "yes", "y"}:
        return True

    if normalized in {"false", "0", "no", "n"}:
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def normalize_value(value: Any) -> Any:
    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass

    return value


def null_if_nan(value: Any) -> Any:
    return None if pd.isna(value) else normalize_value(value)


ROW_PREPROCESSORS: dict[str, Callable[[Any], tuple[Any, ...]]] = {
    "machine": lambda r: (
        normalize_value(r.machine_id),
        normalize_value(r.machine_name),
        normalize_value(r.manufacturer),
        normalize_value(r.model),
        normalize_value(r.machine_type),
    ),
    "operation": lambda r: (
        normalize_value(r.operation_id),
        normalize_value(r.operation_name),
        null_if_nan(r.ideal_cycle_time_sec),
    ),
    "state_mapping": lambda r: (
        normalize_value(r.detailed_state_code),
        normalize_value(r.detailed_state_name),
        normalize_value(r.state_tag),
        normalize_value(r.oee_loss_type),
    ),
    "machine_state_event": lambda r: (
        normalize_value(r.ts),
        normalize_value(r.machine_id),
        normalize_value(r.detailed_state_code),
        normalize_value(r.state_tag),
        null_if_nan(r.reason_code),
        parse_bool(r.is_planned_stop),
        null_if_nan(r.idle_reason),
    ),
    "cycle_event": lambda r: (
        normalize_value(r.cycle_id),
        normalize_value(r.machine_id),
        normalize_value(r.operation_id),
        normalize_value(r.cycle_start_ts),
        normalize_value(r.cycle_end_ts),
        null_if_nan(r.actual_cycle_time_sec),
        normalize_value(r.part_result),
        null_if_nan(r.scrap_reason),
    ),
    "energy_measurement": lambda r: (
        normalize_value(r.ts),
        normalize_value(r.machine_id),
        null_if_nan(r.power_kw),
        null_if_nan(r.energy_kwh_cumulative),
        null_if_nan(r.sample_interval_sec),
    ),
}


def read_seed_csv(table_name: str) -> pd.DataFrame:
    csv_path = SEEDS_DIR / f"{table_name}.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Missing seed file: {csv_path}")

    return pd.read_csv(csv_path)


def truncate_base_tables(conn: psycopg.Connection) -> None:
    """Egyetlen CASCADE TRUNCATE — a downstream enriched/summary táblák
    is ürülnek, így a build_enriched.py tisztán újraépítheti őket."""
    table_list = ", ".join(TABLE_TRUNCATE_ORDER)
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table_list} CASCADE;")


def bulk_copy_table(
    conn: psycopg.Connection,
    table_name: str,
    df: pd.DataFrame,
) -> None:
    columns = TABLE_COLUMNS[table_name]
    preprocess_row = ROW_PREPROCESSORS[table_name]
    column_sql = ", ".join(columns)
    copy_sql = f"COPY {table_name} ({column_sql}) FROM STDIN"

    with conn.cursor() as cur:
        with cur.copy(copy_sql) as copy:
            for row in df.itertuples(index=False, name="Row"):
                copy.write_row(preprocess_row(row))


def main() -> None:
    config = DatabaseConfig.from_env()

    print("Data loading started.")
    print(f"Project base directory: {BASE_DIR}")
    print(f"Seed directory: {SEEDS_DIR}")
    print(f"Connecting to database: {config.dbname} on {config.host}:{config.port}")

    dataframes = {
        table_name: read_seed_csv(table_name)
        for table_name in TABLE_LOAD_ORDER
    }

    with psycopg.connect(**config.to_psycopg_kwargs()) as conn:
        truncate_base_tables(conn)

        for table_name in TABLE_LOAD_ORDER:
            bulk_copy_table(conn, table_name, dataframes[table_name])
            print(f"Loaded {len(dataframes[table_name])} rows into {table_name}.")

        conn.commit()

    print("Data loading finished successfully.")


if __name__ == "__main__":
    main()