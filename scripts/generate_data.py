from pathlib import Path
from datetime import datetime, timedelta, UTC

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
SEEDS_DIR = BASE_DIR / "db" / "seeds"

RANDOM_SEED = 42
RNG = np.random.default_rng(RANDOM_SEED)

START_TS = datetime(2026, 3, 1, 6, 0, tzinfo=UTC)
HOURS_TO_GENERATE = 720
END_TS = START_TS + timedelta(hours=HOURS_TO_GENERATE)

MACHINE_ID = "DMU50_001"
CUMULATIVE_START_KWH = 1000.0
SAMPLE_INTERVAL_SEC = 60

STATE_DEFINITIONS = {
    "RUN": {
        "state_tag": "termelő",
        "reason_code": None,
        "is_planned_stop": False,
        "idle_reason": None,
        "min_duration_min": 6,
        "max_duration_min": 14,
        "weight": 0.60,
    },
    "MICRO_STOP": {
        "state_tag": "nem termelő",
        "reason_code": None,
        "is_planned_stop": False,
        "idle_reason": None,
        "min_duration_min": 1,
        "max_duration_min": 2,
        "weight": 0.15,
    },
    "IDLE": {
        "state_tag": "nem termelő",
        "reason_code": None,
        "is_planned_stop": False,
        "idle_reason": "simple_waiting",
        "min_duration_min": 2,
        "max_duration_min": 4,
        "weight": 0.15,
    },
    "FAILURE": {
        "state_tag": "nem termelő és áll",
        "reason_code": "E101",
        "is_planned_stop": False,
        "idle_reason": None,
        "min_duration_min": 2,
        "max_duration_min": 5,
        "weight": 0.10,
    },
}

OPERATION_SEQUENCE = ["OP_001", "OP_001", "OP_002", "OP_003"]


def generate_machine() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "machine_id": MACHINE_ID,
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


def build_segments() -> list[dict]:
    segments = []
    current_ts = START_TS
    previous_state = None

    state_codes = list(STATE_DEFINITIONS.keys())
    weights = np.array([STATE_DEFINITIONS[s]["weight"] for s in state_codes], dtype=float)
    weights = weights / weights.sum()

    while current_ts < END_TS:
        remaining_minutes = max(
            1,
            int((END_TS - current_ts).total_seconds() // 60)
        )

        if not segments:
            chosen_state = "RUN"
        else:
            chosen_state = RNG.choice(state_codes, p=weights)

            retry_count = 0
            while chosen_state == previous_state and retry_count < 10:
                chosen_state = RNG.choice(state_codes, p=weights)
                retry_count += 1

        state_def = STATE_DEFINITIONS[chosen_state]

        duration_min = int(
            RNG.integers(
                state_def["min_duration_min"],
                state_def["max_duration_min"] + 1
            )
        )
        duration_min = min(duration_min, remaining_minutes)

        start_ts = current_ts
        end_ts = start_ts + timedelta(minutes=duration_min)

        segments.append(
            {
                "start_ts": start_ts,
                "end_ts": end_ts,
                "detailed_state_code": chosen_state,
                "state_tag": state_def["state_tag"],
                "reason_code": state_def["reason_code"],
                "is_planned_stop": state_def["is_planned_stop"],
                "idle_reason": state_def["idle_reason"],
            }
        )

        previous_state = chosen_state
        current_ts = end_ts

    has_run = any(seg["detailed_state_code"] == "RUN" for seg in segments)
    has_non_productive = any(seg["detailed_state_code"] != "RUN" for seg in segments)

    if not has_run and segments:
        segments[0]["detailed_state_code"] = "RUN"
        segments[0]["state_tag"] = STATE_DEFINITIONS["RUN"]["state_tag"]
        segments[0]["reason_code"] = STATE_DEFINITIONS["RUN"]["reason_code"]
        segments[0]["idle_reason"] = STATE_DEFINITIONS["RUN"]["idle_reason"]

    if not has_non_productive and len(segments) > 1:
        segments[-1]["detailed_state_code"] = "IDLE"
        segments[-1]["state_tag"] = STATE_DEFINITIONS["IDLE"]["state_tag"]
        segments[-1]["reason_code"] = STATE_DEFINITIONS["IDLE"]["reason_code"]
        segments[-1]["idle_reason"] = STATE_DEFINITIONS["IDLE"]["idle_reason"]

    return segments


def generate_machine_state_event(segments: list[dict]) -> pd.DataFrame:
    rows = []
    for seg in segments:
        rows.append(
            {
                "ts": seg["start_ts"],
                "machine_id": MACHINE_ID,
                "detailed_state_code": seg["detailed_state_code"],
                "state_tag": seg["state_tag"],
                "reason_code": seg["reason_code"],
                "is_planned_stop": seg["is_planned_stop"],
                "idle_reason": seg["idle_reason"],
            }
        )
    return pd.DataFrame(rows)


def generate_cycle_event(operation_df: pd.DataFrame, segments: list[dict]) -> pd.DataFrame:
    ideal_times = dict(
        zip(operation_df["operation_id"], operation_df["ideal_cycle_time_sec"])
    )

    rows = []
    cycle_counter = 1
    operation_counter = 0

    for seg in segments:
        if seg["detailed_state_code"] != "RUN":
            continue

        current_ts = seg["start_ts"]

        while current_ts < seg["end_ts"]:
            operation_id = OPERATION_SEQUENCE[operation_counter % len(OPERATION_SEQUENCE)]
            operation_counter += 1

            ideal_cycle_time_sec = ideal_times[operation_id]
            performance_factor = float(RNG.uniform(0.96, 1.08))
            actual_cycle_time_sec = round(ideal_cycle_time_sec * performance_factor, 3)

            cycle_end_ts = current_ts + timedelta(seconds=actual_cycle_time_sec)
            if cycle_end_ts > seg["end_ts"]:
                break

            is_scrap = (cycle_counter % 3 == 0)
            rows.append(
                {
                    "cycle_id": f"CYCLE_{cycle_counter:04d}",
                    "machine_id": MACHINE_ID,
                    "operation_id": operation_id,
                    "cycle_start_ts": current_ts,
                    "cycle_end_ts": cycle_end_ts,
                    "actual_cycle_time_sec": actual_cycle_time_sec,
                    "part_result": "scrap" if is_scrap else "good",
                    "scrap_reason": "surface_defect" if is_scrap else None,
                }
            )

            cycle_counter += 1
            current_ts = cycle_end_ts

    return pd.DataFrame(rows)


def find_active_segment(ts: datetime, segments: list[dict]) -> dict | None:
    for seg in segments:
        if seg["start_ts"] <= ts < seg["end_ts"]:
            return seg
    return None


def find_active_cycle(ts: datetime, cycle_df: pd.DataFrame) -> pd.Series | None:
    if cycle_df.empty:
        return None

    matched = cycle_df[
        (cycle_df["cycle_start_ts"] <= ts) & (ts < cycle_df["cycle_end_ts"])
    ]
    if matched.empty:
        return None
    return matched.iloc[0]


def generate_energy_measurement(segments: list[dict], cycle_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    cumulative_kwh = CUMULATIVE_START_KWH

    ts = START_TS
    while ts < END_TS:
        active_segment = find_active_segment(ts, segments)
        active_cycle = find_active_cycle(ts, cycle_df)

        if active_segment is None:
            state_code = "IDLE"
        else:
            state_code = active_segment["detailed_state_code"]

        if state_code == "RUN":
            if active_cycle is not None:
                power_kw = float(RNG.normal(15.0, 0.5))
            else:
                power_kw = float(RNG.normal(9.0, 0.4))
        elif state_code == "MICRO_STOP":
            power_kw = float(RNG.normal(8.0, 0.3))
        elif state_code == "IDLE":
            power_kw = float(RNG.normal(4.2, 0.2))
        elif state_code == "FAILURE":
            power_kw = float(RNG.normal(3.5, 0.2))
        else:
            power_kw = float(RNG.normal(5.0, 0.2))

        power_kw = round(max(power_kw, 0.1), 3)
        delta_kwh = power_kw * (SAMPLE_INTERVAL_SEC / 3600.0)
        cumulative_kwh = round(cumulative_kwh + delta_kwh, 5)

        rows.append(
            {
                "ts": ts,
                "machine_id": MACHINE_ID,
                "power_kw": power_kw,
                "energy_kwh_cumulative": cumulative_kwh,
                "sample_interval_sec": float(SAMPLE_INTERVAL_SEC),
            }
        )

        ts = ts + timedelta(seconds=SAMPLE_INTERVAL_SEC)

    return pd.DataFrame(rows)


def main() -> None:
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)

    machine_df = generate_machine()
    operation_df = generate_operation()
    state_mapping_df = generate_state_mapping()

    segments = build_segments()
    machine_state_event_df = generate_machine_state_event(segments)
    cycle_event_df = generate_cycle_event(operation_df, segments)
    energy_measurement_df = generate_energy_measurement(segments, cycle_event_df)

    files = {
        "machine.csv": machine_df,
        "operation.csv": operation_df,
        "state_mapping.csv": state_mapping_df,
        "machine_state_event.csv": machine_state_event_df,
        "cycle_event.csv": cycle_event_df,
        "energy_measurement.csv": energy_measurement_df,
    }

    for filename, df in files.items():
        output_path = SEEDS_DIR / filename
        df.to_csv(output_path, index=False)
        print(f"Generated file: {output_path}")

    print(f"Random seed: {RANDOM_SEED}")
    print(f"Generation window: {START_TS} -> {END_TS}")
    print(f"machine rows: {len(machine_df)}")
    print(f"operation rows: {len(operation_df)}")
    print(f"state_mapping rows: {len(state_mapping_df)}")
    print(f"machine_state_event rows: {len(machine_state_event_df)}")
    print(f"cycle_event rows: {len(cycle_event_df)}")
    print(f"energy_measurement rows: {len(energy_measurement_df)}")


if __name__ == "__main__":
    main()