import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
REGRESSION_DIR = BASE_DIR / "analysis_outputs" / "regression"

PRIMARY_TARGET = "system_energy_per_good_part_kwh"
SECONDARY_TARGET = "cycle_energy_per_good_part_kwh"
PRIMARY_MODEL = "gamma_glm"
SECONDARY_MODEL = "gamma_glm"
SIGNIFICANCE_LEVEL = 0.05


def load_csv(filename: str) -> pd.DataFrame:
    path = REGRESSION_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Hiányzó fájl: {path}")
    return pd.read_csv(path)


def safe_float(value):
    if pd.isna(value):
        return None
    return float(value)


def get_model_metrics(metrics_df: pd.DataFrame, target: str, model_type: str) -> dict:
    row = metrics_df[
        (metrics_df["target"] == target) &
        (metrics_df["model_type"] == model_type)
    ].iloc[0]

    return {
        "target": target,
        "model_type": model_type,
        "n_obs": int(row["n_obs"]),
        "aic": safe_float(row["aic"]),
        "bic": safe_float(row["bic"]),
        "rsquared": safe_float(row["rsquared"]),
        "rsquared_adj": safe_float(row["rsquared_adj"]),
        "deviance": safe_float(row["deviance"]),
        "null_deviance": safe_float(row["null_deviance"]),
        "pseudo_r2": safe_float(row["pseudo_r2"]),
    }


def get_significant_coefficients(coeff_df: pd.DataFrame, target: str, model_type: str) -> list[dict]:
    subset = coeff_df[
        (coeff_df["target"] == target) &
        (coeff_df["model_type"] == model_type) &
        (coeff_df["parameter"] != "const")
    ].copy()

    subset["is_significant"] = subset["p_value"] < SIGNIFICANCE_LEVEL
    subset = subset.sort_values(["is_significant", "p_value"], ascending=[False, True])

    rows = []
    for _, row in subset.iterrows():
        direction = "csökkenti" if row["coefficient"] < 0 else "növeli"
        rows.append(
            {
                "feature": row["parameter"],
                "coefficient": safe_float(row["coefficient"]),
                "p_value": safe_float(row["p_value"]),
                "ci_lower": safe_float(row["ci_lower"]),
                "ci_upper": safe_float(row["ci_upper"]),
                "is_significant": bool(row["is_significant"]),
                "direction": direction,
            }
        )
    return rows


def get_sensitivity_rows(sens_df: pd.DataFrame, target: str, model_type: str) -> list[dict]:
    subset = sens_df[
        (sens_df["target"] == target) &
        (sens_df["model_type"] == model_type)
    ].copy()

    subset = subset.sort_values("absolute_effect_rank")

    rows = []
    for _, row in subset.iterrows():
        rows.append(
            {
                "feature": row["feature"],
                "beta": safe_float(row["beta"]),
                "estimated_pct_change_for_1pp": safe_float(row["estimated_pct_change_for_1pp"]),
                "direction": row["direction"],
                "p_value": safe_float(row["p_value"]),
                "absolute_effect_rank": safe_float(row["absolute_effect_rank"]),
                "is_significant": bool(row["p_value"] < SIGNIFICANCE_LEVEL),
            }
        )
    return rows


def get_univariate_rows(univariate_df: pd.DataFrame) -> list[dict]:
    rows = []
    for _, row in univariate_df.sort_values("p_value").iterrows():
        rows.append(
            {
                "feature": row["feature"],
                "beta": safe_float(row["beta"]),
                "p_value": safe_float(row["p_value"]),
                "ci_lower": safe_float(row["ci_lower"]),
                "ci_upper": safe_float(row["ci_upper"]),
                "estimated_pct_change_for_1pp": safe_float(row["estimated_pct_change_for_1pp"]),
                "direction": row["direction"],
                "aic": safe_float(row["aic"]),
                "pseudo_r2": safe_float(row["pseudo_r2"]),
                "is_significant": bool(row["p_value"] < SIGNIFICANCE_LEVEL),
            }
        )
    return rows


def get_vif_rows(vif_df: pd.DataFrame) -> list[dict]:
    rows = []
    for _, row in vif_df.iterrows():
        rows.append(
            {
                "feature": row["feature"],
                "vif": safe_float(row["vif"]),
            }
        )
    return rows


def build_draft_key_messages(primary_sens: list[dict], secondary_sens: list[dict]) -> dict:
    primary_sig = [r for r in primary_sens if r["is_significant"]]
    secondary_sig = [r for r in secondary_sens if r["is_significant"]]

    primary_main = primary_sig[0] if primary_sig else None
    secondary_main = secondary_sig[0] if secondary_sig else None

    messages = {
        "primary_main_message": None,
        "secondary_main_message": None,
        "comparison_message": None,
    }

    if primary_main:
        messages["primary_main_message"] = (
            f"A főmodell alapján 1 százalékpontos {primary_main['feature']} javulás "
            f"várhatóan {abs(primary_main['estimated_pct_change_for_1pp']):.3f}%-kal "
            f"{primary_main['direction']} az egy jó darabra jutó teljes rendszerenergia-fogyasztást."
        )

    if secondary_main:
        messages["secondary_main_message"] = (
            f"A ciklusalapú modell alapján 1 százalékpontos {secondary_main['feature']} javulás "
            f"várhatóan {abs(secondary_main['estimated_pct_change_for_1pp']):.3f}%-kal "
            f"{secondary_main['direction']} az egy jó darabra jutó ciklusenergia-fogyasztást."
        )

    if primary_main and secondary_main:
        messages["comparison_message"] = (
            f"A két célváltozó összevetése alapján a rendszer szintű energiaintenzitást "
            f"elsősorban a(z) {primary_main['feature']} befolyásolja, míg a ciklusalapú "
            f"energiaintenzitásban a(z) {secondary_main['feature']} szerepe erősebb."
        )

    return messages


def build_markdown(summary: dict) -> str:
    p = summary["primary_model"]
    s = summary["secondary_model"]

    lines = []
    lines.append("# Regressziós összefoglaló")
    lines.append("")
    lines.append("## Főmodell")
    lines.append(f"- Célváltozó: `{p['target']}`")
    lines.append(f"- Modell: `{p['model_type']}`")
    lines.append(f"- Megfigyelések száma: {p['metrics']['n_obs']}")
    lines.append(
        f"- Pseudo R²: {p['metrics']['pseudo_r2']:.6f}"
        if p["metrics"]["pseudo_r2"] is not None
        else "- Pseudo R²: nincs"
    )
    lines.append("")
    lines.append("### Szignifikáns hatások")
    for row in p["significant_coefficients"]:
        if row["is_significant"]:
            lines.append(
                f"- {row['feature']}: koefficiens = {row['coefficient']:.6f}, p = {row['p_value']:.6g}, irány = {row['direction']}"
            )

    lines.append("")
    lines.append("## Másodlagos modell")
    lines.append(f"- Célváltozó: `{s['target']}`")
    lines.append(f"- Modell: `{s['model_type']}`")
    lines.append(f"- Megfigyelések száma: {s['metrics']['n_obs']}")
    lines.append(
        f"- Pseudo R²: {s['metrics']['pseudo_r2']:.6f}"
        if s["metrics"]["pseudo_r2"] is not None
        else "- Pseudo R²: nincs"
    )
    lines.append("")
    lines.append("### Szignifikáns hatások")
    for row in s["significant_coefficients"]:
        if row["is_significant"]:
            lines.append(
                f"- {row['feature']}: koefficiens = {row['coefficient']:.6f}, p = {row['p_value']:.6g}, irány = {row['direction']}"
            )

    lines.append("")
    lines.append("## VIF")
    for row in summary["vif"]:
        lines.append(f"- {row['feature']}: {row['vif']:.6f}")

    return "\n".join(lines)


def main() -> None:
    metrics_df = load_csv("regression_model_metrics.csv")
    coeff_df = load_csv("regression_coefficients.csv")
    sens_df = load_csv("regression_sensitivity.csv")
    primary_univariate_df = load_csv("primary_univariate_gamma_glm.csv")
    secondary_univariate_df = load_csv("secondary_univariate_gamma_glm.csv")
    primary_vif_df = load_csv("primary_vif.csv")

    primary_metrics = get_model_metrics(metrics_df, PRIMARY_TARGET, PRIMARY_MODEL)
    secondary_metrics = get_model_metrics(metrics_df, SECONDARY_TARGET, SECONDARY_MODEL)

    primary_coeffs = get_significant_coefficients(coeff_df, PRIMARY_TARGET, PRIMARY_MODEL)
    secondary_coeffs = get_significant_coefficients(coeff_df, SECONDARY_TARGET, SECONDARY_MODEL)

    primary_sens = get_sensitivity_rows(sens_df, PRIMARY_TARGET, PRIMARY_MODEL)
    secondary_sens = get_sensitivity_rows(sens_df, SECONDARY_TARGET, SECONDARY_MODEL)

    summary = {
        "significance_level": SIGNIFICANCE_LEVEL,
        "primary_model": {
            "target": PRIMARY_TARGET,
            "model_type": PRIMARY_MODEL,
            "metrics": primary_metrics,
            "significant_coefficients": primary_coeffs,
            "sensitivity": primary_sens,
            "univariate_gamma_glm": get_univariate_rows(primary_univariate_df),
        },
        "secondary_model": {
            "target": SECONDARY_TARGET,
            "model_type": SECONDARY_MODEL,
            "metrics": secondary_metrics,
            "significant_coefficients": secondary_coeffs,
            "sensitivity": secondary_sens,
            "univariate_gamma_glm": get_univariate_rows(secondary_univariate_df),
        },
        "vif": get_vif_rows(primary_vif_df),
    }

    summary["draft_key_messages"] = build_draft_key_messages(primary_sens, secondary_sens)

    json_path = REGRESSION_DIR / "regression_summary.json"
    md_path = REGRESSION_DIR / "regression_summary.md"

    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    md_path.write_text(
        build_markdown(summary),
        encoding="utf-8",
    )

    print("Regression summary build finished successfully.")
    print(f"JSON summary saved to: {json_path}")
    print(f"Markdown summary saved to: {md_path}")

    print("\nPrimary draft message:")
    print(summary["draft_key_messages"]["primary_main_message"])

    print("\nSecondary draft message:")
    print(summary["draft_key_messages"]["secondary_main_message"])

    print("\nComparison draft message:")
    print(summary["draft_key_messages"]["comparison_message"])


if __name__ == "__main__":
    main()