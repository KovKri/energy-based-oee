import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg
from dotenv import load_dotenv

from regression_config import (
    AGGREGATION_HOURS,
    MIN_GOOD_PARTS_FOR_REGRESSION,
    OUTPUT_DIR,
    RAW_HOURLY_EXPORT,
    AGGREGATED_EXPORT,
    PRIMARY_TARGET,
    SECONDARY_TARGET,
)


BASE_DIR = Path(__file__).resolve().parent.parent


def load_regression_base_hourly() -> pd.DataFrame:
    load_dotenv()

    db_name = os.getenv("POSTGRES_DB")
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_host = "localhost"

    query = """
    SELECT
        bucket_start,
        machine_id,
        planned_time_sec,
        availability_loss_sec,
        ideal_cycle_time_total_sec,
        actual_cycle_time_total_sec,
        total_parts,
        good_parts,
        scrap_parts,
        energy_total_kwh,
        energy_productive_kwh,
        energy_non_productive_kwh,
        energy_non_productive_stop_kwh,
        good_cycle_energy_kwh,
        availability,
        performance,
        quality,
        oee,
        scrap_rate,
        cycle_energy_per_good_part_kwh,
        system_energy_per_good_part_kwh,
        non_productive_energy_ratio
    FROM regression_base_hourly
    ORDER BY bucket_start, machine_id;
    """

    with psycopg.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password,
    ) as conn:
        df = pd.read_sql_query(query, conn)

    return df


def aggregate_regression_input(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    df = df.copy()
    df["bucket_start"] = pd.to_datetime(df["bucket_start"], utc=True)

    # Konfigurálható aggregáció
    df["agg_bucket_start"] = df["bucket_start"].dt.floor(f"{AGGREGATION_HOURS}h")

    grouped = (
        df.groupby(["agg_bucket_start", "machine_id"], as_index=False)
        .agg(
            planned_time_sec=("planned_time_sec", "sum"),
            availability_loss_sec=("availability_loss_sec", "sum"),
            ideal_cycle_time_total_sec=("ideal_cycle_time_total_sec", "sum"),
            actual_cycle_time_total_sec=("actual_cycle_time_total_sec", "sum"),
            total_parts=("total_parts", "sum"),
            good_parts=("good_parts", "sum"),
            scrap_parts=("scrap_parts", "sum"),
            energy_total_kwh=("energy_total_kwh", "sum"),
            energy_productive_kwh=("energy_productive_kwh", "sum"),
            energy_non_productive_kwh=("energy_non_productive_kwh", "sum"),
            energy_non_productive_stop_kwh=("energy_non_productive_stop_kwh", "sum"),
            good_cycle_energy_kwh=("good_cycle_energy_kwh", "sum"),
        )
    )

    result = grouped.rename(columns={"agg_bucket_start": "bucket_start"})

    # KPI-k újraszámítása az aggregált nyers komponensekből
    result["availability"] = np.where(
        result["planned_time_sec"] > 0,
        (result["planned_time_sec"] - result["availability_loss_sec"]) / result["planned_time_sec"],
        0.0,
    )

    result["performance"] = np.where(
        result["actual_cycle_time_total_sec"] > 0,
        result["ideal_cycle_time_total_sec"] / result["actual_cycle_time_total_sec"],
        0.0,
    )

    result["quality"] = np.where(
        result["total_parts"] > 0,
        result["good_parts"] / result["total_parts"],
        0.0,
    )

    result["oee"] = (
        result["availability"]
        * result["performance"]
        * result["quality"]
    )

    result["scrap_rate"] = np.where(
        result["total_parts"] > 0,
        result["scrap_parts"] / result["total_parts"],
        0.0,
    )

    result["cycle_energy_per_good_part_kwh"] = np.where(
        result["good_parts"] > 0,
        result["good_cycle_energy_kwh"] / result["good_parts"],
        0.0,
    )

    result["system_energy_per_good_part_kwh"] = np.where(
        result["good_parts"] > 0,
        result["energy_total_kwh"] / result["good_parts"],
        0.0,
    )

    result["non_productive_energy_ratio"] = np.where(
        result["energy_total_kwh"] > 0,
        (result["energy_non_productive_kwh"] + result["energy_non_productive_stop_kwh"])
        / result["energy_total_kwh"],
        0.0,
    )

    # Szűrés a minimális jó darabszám alapján
    result = result[result["good_parts"] >= MIN_GOOD_PARTS_FOR_REGRESSION].copy()

    # Hasznos oszlopsorrend
    result = result[
        [
            "bucket_start",
            "machine_id",
            "availability",
            "performance",
            "quality",
            "oee",
            "good_parts",
            "total_parts",
            "scrap_parts",
            "scrap_rate",
            "energy_total_kwh",
            "energy_productive_kwh",
            "energy_non_productive_kwh",
            "energy_non_productive_stop_kwh",
            "good_cycle_energy_kwh",
            "cycle_energy_per_good_part_kwh",
            "system_energy_per_good_part_kwh",
            "non_productive_energy_ratio",
            "planned_time_sec",
            "availability_loss_sec",
            "ideal_cycle_time_total_sec",
            "actual_cycle_time_total_sec",
        ]
    ]

    return result


def export_outputs(raw_df: pd.DataFrame, aggregated_df: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = OUTPUT_DIR / RAW_HOURLY_EXPORT
    aggregated_path = OUTPUT_DIR / AGGREGATED_EXPORT
    metadata_path = OUTPUT_DIR / "regression_input_metadata.json"

    raw_df.to_csv(raw_path, index=False)
    aggregated_df.to_csv(aggregated_path, index=False)

    metadata = {
        "aggregation_hours": AGGREGATION_HOURS,
        "min_good_parts_for_regression": MIN_GOOD_PARTS_FOR_REGRESSION,
        "primary_target": PRIMARY_TARGET,
        "secondary_target": SECONDARY_TARGET,
        "raw_rows": int(len(raw_df)),
        "aggregated_rows_after_filtering": int(len(aggregated_df)),
    }

    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Raw hourly export saved to: {raw_path}")
    print(f"Aggregated regression export saved to: {aggregated_path}")
    print(f"Metadata saved to: {metadata_path}")


def print_preview(df: pd.DataFrame, title: str, rows: int = 10) -> None:
    print(f"\n{title}")
    if df.empty:
        print("Nincs megjeleníthető adat.")
        return
    print(df.head(rows).to_string(index=False))


def main() -> None:
    print("Regression input preparation started.")
    print(f"Aggregation hours: {AGGREGATION_HOURS}")
    print(f"Minimum good parts for regression: {MIN_GOOD_PARTS_FOR_REGRESSION}")

    raw_df = load_regression_base_hourly()
    aggregated_df = aggregate_regression_input(raw_df)

    export_outputs(raw_df, aggregated_df)

    print(f"\nRaw hourly rows: {len(raw_df)}")
    print(f"Aggregated rows after filtering: {len(aggregated_df)}")

    if not aggregated_df.empty:
        print(
            "\nTarget preview:"
            f"\n- {PRIMARY_TARGET}: min={aggregated_df[PRIMARY_TARGET].min():.4f},"
            f" max={aggregated_df[PRIMARY_TARGET].max():.4f},"
            f" mean={aggregated_df[PRIMARY_TARGET].mean():.4f}"
        )
        print(
            f"- {SECONDARY_TARGET}: min={aggregated_df[SECONDARY_TARGET].min():.4f},"
            f" max={aggregated_df[SECONDARY_TARGET].max():.4f},"
            f" mean={aggregated_df[SECONDARY_TARGET].mean():.4f}"
        )

    print_preview(raw_df, "Raw hourly regression base preview:")
    print_preview(aggregated_df, "Aggregated regression input preview:")


if __name__ == "__main__":
    main()