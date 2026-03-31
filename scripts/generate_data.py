from pathlib import Path
from datetime import datetime, timedelta, UTC

import pandas as pd
import numpy as np


BASE_DIR = Path(__file__).resolve().parent.parent
SEEDS_DIR = BASE_DIR / "db" / "seeds"
RANDOM_SEED = 42
START_TS = datetime(2026, 3, 1, 6, 0, tzinfo=UTC)
HOURS_TO_GENERATE = 24
END_TS = START_TS + timedelta(hours=HOURS_TO_GENERATE)


def generate_machine() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "machine_id": "DMU50_001",
                "machine_name": "DMG MORI DMU 50 3rd Generation",
                "manufacturer": "DMG MORI",
                "model": "DMU 50 3rd Generation",
                "machine_type": "5-axis CNC machining center",
            }
        ]
    )

def generate_operation() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "operation_id": "OP_001",
                "operation_name": "Aluminium housing rough machining",
                "ideal_cycle_time_sec": 480.0,
            },
            {
                "operation_id": "OP_002",
                "operation_name": "Aluminium housing finish machining",
                "ideal_cycle_time_sec": 540.0,
            },
            {
                "operation_id": "OP_003",
                "operation_name": "Bracket 5-axis drilling and milling",
                "ideal_cycle_time_sec": 360.0,
            },
        ]
    )

def generate_state_mapping() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "detailed_state_code": "RUN",
                "detailed_state_name": "Running",
                "state_tag": "termelő",
                "oee_loss_type": None,
            },
            {
                "detailed_state_code": "IDLE",
                "detailed_state_name": "Idle",
                "state_tag": "nem termelő",
                "oee_loss_type": None,
            },
            {
                "detailed_state_code": "MICRO_STOP",
                "detailed_state_name": "Micro-stop",
                "state_tag": "nem termelő",
                "oee_loss_type": "Performance",
            },
            {
                "detailed_state_code": "FAILURE",
                "detailed_state_name": "Failure",
                "state_tag": "nem termelő és áll",
                "oee_loss_type": "Availability",
            },
        ]
    )

def generate_machine_state_event() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ts": START_TS,
                "machine_id": "DMU50_001",
                "detailed_state_code": "RUN",
                "state_tag": "termelő",
                "reason_code": None,
                "is_planned_stop": False,
                "idle_reason": None,
            },
            {
                "ts": START_TS + timedelta(hours=2),
                "machine_id": "DMU50_001",
                "detailed_state_code": "MICRO_STOP",
                "state_tag": "nem termelő",
                "reason_code": None,
                "is_planned_stop": False,
                "idle_reason": None,
            },
            {
                "ts": START_TS + timedelta(hours=2, minutes=5),
                "machine_id": "DMU50_001",
                "detailed_state_code": "IDLE",
                "state_tag": "nem termelő",
                "reason_code": None,
                "is_planned_stop": False,
                "idle_reason": "simple_waiting",
            },
            {
                "ts": START_TS + timedelta(hours=3),
                "machine_id": "DMU50_001",
                "detailed_state_code": "FAILURE",
                "state_tag": "nem termelő és áll",
                "reason_code": "E101",
                "is_planned_stop": False,
                "idle_reason": None,
            },
            {
                "ts": START_TS + timedelta(hours=4),
                "machine_id": "DMU50_001",
                "detailed_state_code": "RUN",
                "state_tag": "termelő",
                "reason_code": None,
                "is_planned_stop": False,
                "idle_reason": None,
            },
        ]
    )

def generate_cycle_event() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "cycle_id": "CYCLE_0001",
                "machine_id": "DMU50_001",
                "operation_id": "OP_001",
                "cycle_start_ts": START_TS + timedelta(minutes=5),
                "cycle_end_ts": START_TS + timedelta(minutes=13),
                "actual_cycle_time_sec": 480.0,
                "part_result": "good",
                "scrap_reason": None,
            },
            {
                "cycle_id": "CYCLE_0002",
                "machine_id": "DMU50_001",
                "operation_id": "OP_001",
                "cycle_start_ts": START_TS + timedelta(minutes=15),
                "cycle_end_ts": START_TS + timedelta(minutes=24),
                "actual_cycle_time_sec": 540.0,
                "part_result": "scrap",
                "scrap_reason": "surface_defect",
            },
            {
                "cycle_id": "CYCLE_0003",
                "machine_id": "DMU50_001",
                "operation_id": "OP_002",
                "cycle_start_ts": START_TS + timedelta(minutes=30),
                "cycle_end_ts": START_TS + timedelta(minutes=39),
                "actual_cycle_time_sec": 540.0,
                "part_result": "good",
                "scrap_reason": None,
            },
        ]
    )

def generate_energy_measurement() -> pd.DataFrame:
    rows = [
        {
            "ts": START_TS + timedelta(minutes=0),
            "machine_id": "DMU50_001",
            "power_kw": 12.5,
            "energy_kwh_cumulative": 1000.00000,
            "sample_interval_sec": 60.0,
        },
        {
            "ts": START_TS + timedelta(minutes=1),
            "machine_id": "DMU50_001",
            "power_kw": 13.2,
            "energy_kwh_cumulative": 1000.22000,
            "sample_interval_sec": 60.0,
        },
        {
            "ts": START_TS + timedelta(minutes=2),
            "machine_id": "DMU50_001",
            "power_kw": 14.1,
            "energy_kwh_cumulative": 1000.45500,
            "sample_interval_sec": 60.0,
        },
        {
            "ts": START_TS + timedelta(minutes=3),
            "machine_id": "DMU50_001",
            "power_kw": 8.0,
            "energy_kwh_cumulative": 1000.58833,
            "sample_interval_sec": 60.0,
        },
        {
            "ts": START_TS + timedelta(minutes=4),
            "machine_id": "DMU50_001",
            "power_kw": 6.5,
            "energy_kwh_cumulative": 1000.69666,
            "sample_interval_sec": 60.0,
        },
    ]
    return pd.DataFrame(rows)


def main() -> None:
    np.random.seed(RANDOM_SEED)
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)

    machine_df = generate_machine()
    operation_df = generate_operation()
    state_mapping_df = generate_state_mapping()
    machine_state_event_df = generate_machine_state_event()
    machine_state_event_output_path = SEEDS_DIR / "machine_state_event.csv"
    machine_state_event_df.to_csv(machine_state_event_output_path, index=False)
    cycle_event_df = generate_cycle_event()
    energy_measurement_df = generate_energy_measurement()
    energy_measurement_output_path = SEEDS_DIR / "energy_measurement.csv"
    energy_measurement_df.to_csv(energy_measurement_output_path, index=False)
    cycle_event_output_path = SEEDS_DIR / "cycle_event.csv"
    cycle_event_df.to_csv(cycle_event_output_path, index=False)
    state_mapping_output_path = SEEDS_DIR / "state_mapping.csv"
    state_mapping_df.to_csv(state_mapping_output_path, index=False)
    operation_output_path = SEEDS_DIR / "operation.csv"
    operation_df.to_csv(operation_output_path, index=False)
    output_path = SEEDS_DIR / "machine.csv"
    machine_df.to_csv(output_path, index=False)

    print("Synthetic data generator started.")
    print(f"Project base directory: {BASE_DIR}")
    print(f"Seeds directory: {SEEDS_DIR}")
    print(f"Generated file: {output_path}")
    print(f"Generated file: {operation_output_path}")
    print(f"Generated file: {state_mapping_output_path}")
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Generation window: {START_TS} -> {END_TS}")
    print(f"Generated file: {machine_state_event_output_path}")
    print(f"Generated file: {cycle_event_output_path}")
    print(f"Generated file: {energy_measurement_output_path}")

    print(f"machine rows: {len(machine_df)}")
    print(f"operation rows: {len(operation_df)}")
    print(f"state_mapping rows: {len(state_mapping_df)}")
    print(f"machine_state_event rows: {len(machine_state_event_df)}")
    print(f"cycle_event rows: {len(cycle_event_df)}")
    print(f"energy_measurement rows: {len(energy_measurement_df)}")

if __name__ == "__main__":
    main()