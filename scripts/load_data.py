import os
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
SEEDS_DIR = BASE_DIR / "db" / "seeds"


def null_if_nan(value):
    if pd.isna(value):
        return None
    return value


def main() -> None:
    load_dotenv()

    db_name = os.getenv("POSTGRES_DB")
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_host = "localhost"

    print("Data loader started.")
    print(f"Project base directory: {BASE_DIR}")
    print(f"Seeds directory: {SEEDS_DIR}")
    print(f"Connecting to database: {db_name} on {db_host}:{db_port}")

    machine_path = SEEDS_DIR / "machine.csv"
    operation_path = SEEDS_DIR / "operation.csv"
    state_mapping_path = SEEDS_DIR / "state_mapping.csv"
    machine_state_event_path = SEEDS_DIR / "machine_state_event.csv"
    cycle_event_path = SEEDS_DIR / "cycle_event.csv"
    energy_measurement_path = SEEDS_DIR / "energy_measurement.csv"

    machine_df = pd.read_csv(machine_path)
    operation_df = pd.read_csv(operation_path)
    state_mapping_df = pd.read_csv(state_mapping_path)
    machine_state_event_df = pd.read_csv(machine_state_event_path)
    cycle_event_df = pd.read_csv(cycle_event_path)
    energy_measurement_df = pd.read_csv(energy_measurement_path)

    print(f"Loaded CSV: {machine_path}")
    print(f"machine rows in CSV: {len(machine_df)}")
    print(f"Loaded CSV: {operation_path}")
    print(f"operation rows in CSV: {len(operation_df)}")
    print(f"Loaded CSV: {state_mapping_path}")
    print(f"state_mapping rows in CSV: {len(state_mapping_df)}")
    print(f"Loaded CSV: {machine_state_event_path}")
    print(f"machine_state_event rows in CSV: {len(machine_state_event_df)}")
    print(f"Loaded CSV: {cycle_event_path}")
    print(f"cycle_event rows in CSV: {len(cycle_event_df)}")
    print(f"Loaded CSV: {energy_measurement_path}")
    print(f"energy_measurement rows in CSV: {len(energy_measurement_df)}")

    with psycopg.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                TRUNCATE TABLE
                    energy_measurement,
                    cycle_event,
                    machine_state_event,
                    state_mapping,
                    operation,
                    machine
                RESTART IDENTITY CASCADE;
                """
            )

            for row in machine_df.itertuples(index=False):
                cur.execute(
                    """
                    INSERT INTO machine (
                        machine_id,
                        machine_name,
                        manufacturer,
                        model,
                        machine_type
                    )
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (
                        row.machine_id,
                        row.machine_name,
                        row.manufacturer,
                        row.model,
                        row.machine_type,
                    ),
                )

            for row in operation_df.itertuples(index=False):
                cur.execute(
                    """
                    INSERT INTO operation (
                        operation_id,
                        operation_name,
                        ideal_cycle_time_sec
                    )
                    VALUES (%s, %s, %s);
                    """,
                    (
                        row.operation_id,
                        row.operation_name,
                        row.ideal_cycle_time_sec,
                    ),
                )

            for row in state_mapping_df.itertuples(index=False):
                cur.execute(
                    """
                    INSERT INTO state_mapping (
                        detailed_state_code,
                        detailed_state_name,
                        state_tag,
                        oee_loss_type
                    )
                    VALUES (%s, %s, %s, %s);
                    """,
                    (
                        row.detailed_state_code,
                        row.detailed_state_name,
                        row.state_tag,
                        null_if_nan(row.oee_loss_type),
                    ),
                )

            for row in machine_state_event_df.itertuples(index=False):
                cur.execute(
                    """
                    INSERT INTO machine_state_event (
                        ts,
                        machine_id,
                        detailed_state_code,
                        state_tag,
                        reason_code,
                        is_planned_stop,
                        idle_reason
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        row.ts,
                        row.machine_id,
                        row.detailed_state_code,
                        row.state_tag,
                        null_if_nan(row.reason_code),
                        bool(row.is_planned_stop),
                        null_if_nan(row.idle_reason),
                    ),
                )

            for row in cycle_event_df.itertuples(index=False):
                cur.execute(
                    """
                    INSERT INTO cycle_event (
                        cycle_id,
                        machine_id,
                        operation_id,
                        cycle_start_ts,
                        cycle_end_ts,
                        actual_cycle_time_sec,
                        part_result,
                        scrap_reason
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        row.cycle_id,
                        row.machine_id,
                        row.operation_id,
                        row.cycle_start_ts,
                        row.cycle_end_ts,
                        row.actual_cycle_time_sec,
                        row.part_result,
                        null_if_nan(row.scrap_reason),
                    ),
                )

            for row in energy_measurement_df.itertuples(index=False):
                cur.execute(
                    """
                    INSERT INTO energy_measurement (
                        ts,
                        machine_id,
                        power_kw,
                        energy_kwh_cumulative,
                        sample_interval_sec
                    )
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (
                        row.ts,
                        row.machine_id,
                        row.power_kw,
                        row.energy_kwh_cumulative,
                        row.sample_interval_sec,
                    ),
                )

        conn.commit()

    print("machine.csv loaded into machine table successfully.")
    print("operation.csv loaded into operation table successfully.")
    print("state_mapping.csv loaded into state_mapping table successfully.")
    print("machine_state_event.csv loaded into machine_state_event table successfully.")
    print("cycle_event.csv loaded into cycle_event table successfully.")
    print("energy_measurement.csv loaded into energy_measurement table successfully.")


if __name__ == "__main__":
    main()