from pathlib import Path
import sys

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from load_data import parse_bool


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        ("true", True),
        ("false", False),
        ("True", True),
        ("False", False),
        ("1", True),
        ("0", False),
        ("yes", True),
        ("no", False),
        ("y", True),
        ("n", False),
    ],
)
def test_parse_bool_valid_values(value, expected):
    assert parse_bool(value) is expected


def test_parse_bool_nan_returns_false():
    import pandas as pd

    assert parse_bool(pd.NA) is False


def test_parse_bool_invalid_value_raises():
    with pytest.raises(ValueError, match="Invalid boolean value"):
        parse_bool("maybe")