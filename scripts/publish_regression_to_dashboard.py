import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
SUMMARY_PATH = BASE_DIR / "analysis_outputs" / "regression" / "regression_summary.json"


FEATURE_LABELS = {
    "availability": "rendelkezésre állás",
    "performance": "teljesítmény",
    "quality": "minőség",
}

TARGET_LABELS = {
    "system_energy_per_good_part_kwh": "Teljes rendszerenergia / jó darab",
    "cycle_energy_per_good_part_kwh": "Ciklusenergia / jó darab",
}

MODEL_LABELS = {
    "gamma_glm": "Gamma GLM",
    "log_ols": "log-OLS",
}


def load_summary() -> dict:
    if not SUMMARY_PATH.exists():
        raise FileNotFoundError(
            f"Nem található a regressziós összefoglaló: {SUMMARY_PATH}\n"
            "Előbb futtasd: python scripts/build_regression_summary.py"
        )

    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def hu_feature_name(feature: str) -> str:
    return FEATURE_LABELS.get(feature, feature)


def hu_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} és {items[1]}"
    return f"{', '.join(items[:-1])} és {items[-1]}"


def get_sig_and_nonsig_features(model_data: dict) -> tuple[list[str], list[str]]:
    significant = []
    non_significant = []

    for row in model_data["significant_coefficients"]:
        feature = row["feature"]
        if row["is_significant"]:
            significant.append(feature)
        else:
            non_significant.append(feature)

    return significant, non_significant


def build_primary_explanation(sig_features: list[str]) -> str:
    if "quality" in sig_features and "availability" in sig_features:
        return (
            "A teljes rendszerenergia / jó darab esetében a minőség és a rendelkezésre állás "
            "javítása csökkentheti az energiaintenzitást."
        )

    sig_hu = [hu_feature_name(f) for f in sig_features]
    if sig_hu:
        return (
            f"A teljes rendszerenergia / jó darab esetében a {hu_list(sig_hu)} "
            f"javítása csökkentheti az energiaintenzitást."
        )

    return (
        "A teljes rendszerenergia / jó darab esetében a modell most nem mutatott egyértelmű, "
        "kiemelhető tényezőt."
    )


def build_secondary_explanation(sig_features: list[str]) -> str:
    if "performance" in sig_features:
        return (
            "A ciklusenergia / jó darab esetében a teljesítmény javítása "
            "csökkentheti az energiaintenzitást."
        )

    sig_hu = [hu_feature_name(f) for f in sig_features]
    if sig_hu:
        return (
            f"A ciklusenergia / jó darab esetében a {hu_list(sig_hu)} "
            f"javítása csökkentheti az energiaintenzitást."
        )

    return (
        "A ciklusenergia / jó darab esetében a modell most nem mutatott egyértelmű, "
        "kiemelhető tényezőt."
    )


def build_sensitivity_message(model_data: dict) -> str:
    significant_rows = [
        row for row in model_data["sensitivity"]
        if row["is_significant"]
    ]

    if not significant_rows:
        return "A modell alapján most nem emelhető ki egyértelmű szenzitivitási megállapítás."

    top_row = min(significant_rows, key=lambda x: x["absolute_effect_rank"])
    feature_hu = hu_feature_name(top_row["feature"])
    pct = abs(float(top_row["estimated_pct_change_for_1pp"]))

    if model_data["target"] == "system_energy_per_good_part_kwh":
        return (
            f"A főmodell alapján 1 százalékpontos {feature_hu}javulás "
            f"várhatóan kb. {pct:.2f}%-kal csökkentheti az egy jó darabra jutó "
            f"teljes rendszerenergia-fogyasztást."
        )

    if model_data["target"] == "cycle_energy_per_good_part_kwh":
        return (
            f"A ciklusalapú modell alapján 1 százalékpontos {feature_hu}javulás "
            f"várhatóan kb. {pct:.2f}%-kal csökkentheti az egy jó darabra jutó "
            f"ciklusenergia-fogyasztást."
        )

    return (
        f"A modell alapján 1 százalékpontos {feature_hu}javulás "
        f"várhatóan kb. {pct:.2f}%-os kedvező változással járhat."
    )


def build_technical_note(model_data: dict, sig_features: list[str], nonsig_features: list[str]) -> str:
    model_label = MODEL_LABELS.get(model_data["model_type"], model_data["model_type"])
    n_obs = model_data["metrics"]["n_obs"]
    pseudo_r2 = model_data["metrics"]["pseudo_r2"]

    sig_hu = [hu_feature_name(f) for f in sig_features]
    nonsig_hu = [hu_feature_name(f) for f in nonsig_features]

    sig_text = hu_list(sig_hu) if sig_hu else "nincs"
    nonsig_text = hu_list(nonsig_hu) if nonsig_hu else "nincs"

    pseudo_r2_text = "n.a." if pseudo_r2 is None else f"{pseudo_r2:.3f}"

    return (
        f"Modell: {model_label}. "
        f"Megfigyelések száma: {n_obs}. "
        f"Pseudo R²: {pseudo_r2_text}. "
        f"Szignifikáns tényezők: {sig_text}. "
        f"Nem szignifikáns tényezők: {nonsig_text}."
    )


def build_row(scope: str, model_data: dict) -> dict:
    sig_features, nonsig_features = get_sig_and_nonsig_features(model_data)

    if scope == "primary":
        display_order = 1
        explanation = build_primary_explanation(sig_features)
    else:
        display_order = 2
        explanation = build_secondary_explanation(sig_features)

    significant_features_text = hu_list([hu_feature_name(f) for f in sig_features])
    non_significant_features_text = hu_list([hu_feature_name(f) for f in nonsig_features])

    technical_note = build_technical_note(model_data, sig_features, nonsig_features)
    sensitivity_message = build_sensitivity_message(model_data)

    return {
        "model_scope": scope,
        "display_order": display_order,
        "target_name": model_data["target"],
        "target_label": TARGET_LABELS.get(model_data["target"], model_data["target"]),
        "model_type": MODEL_LABELS.get(model_data["model_type"], model_data["model_type"]),
        "n_obs": model_data["metrics"]["n_obs"],
        "pseudo_r2": model_data["metrics"]["pseudo_r2"],
        "significant_features": significant_features_text,
        "non_significant_features": non_significant_features_text,
        "headline": "",
        "explanation": explanation,
        "technical_note": technical_note,
        "sensitivity_message": sensitivity_message,
    }


def upsert_dashboard_rows(rows: list[dict]) -> None:
    load_dotenv()

    db_name = os.getenv("POSTGRES_DB")
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_host = "localhost"

    query = """
    INSERT INTO regression_dashboard_summary (
        model_scope,
        display_order,
        updated_at,
        target_name,
        target_label,
        model_type,
        n_obs,
        pseudo_r2,
        significant_features,
        non_significant_features,
        headline,
        explanation,
        technical_note,
        sensitivity_message
    )
    VALUES (
        %(model_scope)s,
        %(display_order)s,
        now(),
        %(target_name)s,
        %(target_label)s,
        %(model_type)s,
        %(n_obs)s,
        %(pseudo_r2)s,
        %(significant_features)s,
        %(non_significant_features)s,
        %(headline)s,
        %(explanation)s,
        %(technical_note)s,
        %(sensitivity_message)s
    )
    ON CONFLICT (model_scope) DO UPDATE SET
        display_order = EXCLUDED.display_order,
        updated_at = now(),
        target_name = EXCLUDED.target_name,
        target_label = EXCLUDED.target_label,
        model_type = EXCLUDED.model_type,
        n_obs = EXCLUDED.n_obs,
        pseudo_r2 = EXCLUDED.pseudo_r2,
        significant_features = EXCLUDED.significant_features,
        non_significant_features = EXCLUDED.non_significant_features,
        headline = EXCLUDED.headline,
        explanation = EXCLUDED.explanation,
        technical_note = EXCLUDED.technical_note,
        sensitivity_message = EXCLUDED.sensitivity_message;
    """

    with psycopg.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password,
    ) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(query, row)
        conn.commit()


def main() -> None:
    summary = load_summary()

    primary_row = build_row("primary", summary["primary_model"])
    secondary_row = build_row("secondary", summary["secondary_model"])

    rows = [primary_row, secondary_row]
    upsert_dashboard_rows(rows)

    print("Regression dashboard publish finished successfully.\n")

    for row in rows:
        print(f"[{row['model_scope']}] {row['target_label']}")
        print(f"Explanation: {row['explanation']}")
        print(f"Sensitivity: {row['sensitivity_message']}")
        print(f"Technical note: {row['technical_note']}")
        print()


if __name__ == "__main__":
    main()