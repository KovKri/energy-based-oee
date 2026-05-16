from pathlib import Path
import sys

import pandas as pd
import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from prepare_regression_input import aggregate_regression_input


def test_aggregate_regression_input_recomputes_kpis_from_raw_components():
    df = pd.DataFrame(
        [
            {
                "bucket_start": "2025-01-01T08:00:00Z",
                "machine_id": 1,
                "planned_time_sec": 3600,
                "availability_loss_sec": 600,
                "ideal_cycle_time_total_sec": 1800,
                "actual_cycle_time_total_sec": 2400,
                "total_parts": 3,
                "good_parts": 2,
                "scrap_parts": 1,
                "energy_total_kwh": 6.0,
                "energy_productive_kwh": 4.5,
                "energy_non_productive_kwh": 1.0,
                "energy_non_productive_stop_kwh": 0.5,
                "good_cycle_energy_kwh": 2.0,
            },
            {
                "bucket_start": "2025-01-01T10:00:00Z",
                "machine_id": 1,
                "planned_time_sec": 3600,
                "availability_loss_sec": 300,
                "ideal_cycle_time_total_sec": 900,
                "actual_cycle_time_total_sec": 1200,
                "total_parts": 2,
                "good_parts": 1,
                "scrap_parts": 1,
                "energy_total_kwh": 3.0,
                "energy_productive_kwh": 2.25,
                "energy_non_productive_kwh": 0.5,
                "energy_non_productive_stop_kwh": 0.25,
                "good_cycle_energy_kwh": 1.0,
            },
        ]
    )

    result = aggregate_regression_input(df)

    assert len(result) == 1

    row = result.iloc[0]

    assert row["machine_id"] == 1
    assert row["bucket_start"] == pd.Timestamp("2025-01-01T08:00:00Z")

    assert row["planned_time_sec"] == 7200
    assert row["availability_loss_sec"] == 900
    assert row["total_parts"] == 5
    assert row["good_parts"] == 3
    assert row["scrap_parts"] == 2
    assert row["energy_total_kwh"] == pytest.approx(9.0)
    assert row["good_cycle_energy_kwh"] == pytest.approx(3.0)

    # availability = (7200 - 900) / 7200 = 0.875
    assert row["availability"] == pytest.approx(0.875)

    # performance = 2700 / 3600 = 0.75
    assert row["performance"] == pytest.approx(0.75)

    # quality = 3 / 5 = 0.6
    assert row["quality"] == pytest.approx(0.6)

    # oee = 0.875 * 0.75 * 0.6 = 0.39375
    assert row["oee"] == pytest.approx(0.39375)

    # scrap_rate = 2 / 5 = 0.4
    assert row["scrap_rate"] == pytest.approx(0.4)

    # cycle_energy_per_good_part_kwh = 3 / 3 = 1.0
    assert row["cycle_energy_per_good_part_kwh"] == pytest.approx(1.0)

    # system_energy_per_good_part_kwh = 9 / 3 = 3.0
    assert row["system_energy_per_good_part_kwh"] == pytest.approx(3.0)

    # non_productive_energy_ratio = (1.0 + 0.5 + 0.5 + 0.25) / 9 = 0.25
    assert row["non_productive_energy_ratio"] == pytest.approx(0.25)