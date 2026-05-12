from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Aggregáció és szűrés
AGGREGATION_HOURS = 4
MIN_GOOD_PARTS_FOR_REGRESSION = 2

# Célváltozók
PRIMARY_TARGET = "system_energy_per_good_part_kwh"
SECONDARY_TARGET = "cycle_energy_per_good_part_kwh"

# Magyarázó változók
BASE_FEATURE_COLUMNS = [
    "availability",
    "performance",
    "quality",
]

# Később ide betehetők kontrollváltozók is, pl.
# ["scrap_rate", "non_productive_energy_ratio"]
OPTIONAL_CONTROL_COLUMNS = []

USE_CONTROL_VARIABLES = False

# Robusztus szórásbecslés OLS-hez
ROBUST_COV_TYPE = "HC3"

# Kimeneti mappa
OUTPUT_DIR = BASE_DIR / "analysis_outputs"
REGRESSION_OUTPUT_DIR = OUTPUT_DIR / "regression"

# Input exportok
RAW_HOURLY_EXPORT = "regression_base_hourly.csv"
AGGREGATED_EXPORT = "regression_input_aggregated.csv"