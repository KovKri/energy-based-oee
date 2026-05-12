import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor

from regression_config import (
    OUTPUT_DIR,
    REGRESSION_OUTPUT_DIR,
    AGGREGATED_EXPORT,
    PRIMARY_TARGET,
    SECONDARY_TARGET,
    BASE_FEATURE_COLUMNS,
    OPTIONAL_CONTROL_COLUMNS,
    USE_CONTROL_VARIABLES,
    ROBUST_COV_TYPE,
)


def get_feature_columns() -> list[str]:
    if USE_CONTROL_VARIABLES:
        return BASE_FEATURE_COLUMNS + OPTIONAL_CONTROL_COLUMNS
    return BASE_FEATURE_COLUMNS.copy()


def load_regression_dataset() -> pd.DataFrame:
    input_path = OUTPUT_DIR / AGGREGATED_EXPORT
    if not input_path.exists():
        raise FileNotFoundError(
            f"Nem található a regressziós input fájl: {input_path}. "
            f"Előbb futtasd: python scripts/prepare_regression_input.py"
        )

    df = pd.read_csv(input_path)
    if "bucket_start" in df.columns:
        df["bucket_start"] = pd.to_datetime(df["bucket_start"], utc=True)

    return df


def prepare_model_df(df: pd.DataFrame, target: str, feature_columns: list[str]) -> pd.DataFrame:
    required_columns = [target] + feature_columns
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Hiányzó oszlopok a regressziós inputból: {missing}")

    model_df = df[["bucket_start", "machine_id"] + required_columns].copy()

    for col in required_columns:
        model_df[col] = pd.to_numeric(model_df[col], errors="coerce")

    model_df = model_df.replace([np.inf, -np.inf], np.nan).dropna()
    model_df = model_df[model_df[target] > 0].copy()

    return model_df


def fit_log_ols(model_df: pd.DataFrame, target: str, feature_columns: list[str]):
    X = sm.add_constant(model_df[feature_columns], has_constant="add")
    y_log = np.log(model_df[target])

    model = sm.OLS(y_log, X)
    result = model.fit(cov_type=ROBUST_COV_TYPE)

    return result, X, y_log


def fit_gamma_glm(model_df: pd.DataFrame, target: str, feature_columns: list[str]):
    X = sm.add_constant(model_df[feature_columns], has_constant="add")
    y = model_df[target]

    model = sm.GLM(
        y,
        X,
        family=sm.families.Gamma(link=sm.families.links.Log())
    )
    result = model.fit()

    return result, X, y


def calculate_vif(model_df: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    X = model_df[feature_columns].copy()
    X = sm.add_constant(X, has_constant="add")

    vif_rows = []
    for i, col in enumerate(X.columns):
        if col == "const":
            continue
        vif_rows.append(
            {
                "feature": col,
                "vif": variance_inflation_factor(X.values, i),
            }
        )

    return pd.DataFrame(vif_rows)


def calculate_breusch_pagan(ols_result, X) -> pd.DataFrame:
    lm_stat, lm_pvalue, f_stat, f_pvalue = het_breuschpagan(ols_result.resid, X)

    return pd.DataFrame(
        [
            {
                "lm_stat": lm_stat,
                "lm_pvalue": lm_pvalue,
                "f_stat": f_stat,
                "f_pvalue": f_pvalue,
            }
        ]
    )


def build_coefficients_table(result, target: str, model_type: str) -> pd.DataFrame:
    conf_int = result.conf_int()
    rows = []

    for param_name, coef in result.params.items():
        rows.append(
            {
                "target": target,
                "model_type": model_type,
                "parameter": param_name,
                "coefficient": coef,
                "p_value": result.pvalues.get(param_name, np.nan),
                "ci_lower": conf_int.loc[param_name, 0],
                "ci_upper": conf_int.loc[param_name, 1],
            }
        )

    return pd.DataFrame(rows)


def build_sensitivity_table(result, target: str, model_type: str, feature_columns: list[str]) -> pd.DataFrame:
    rows = []

    for feature in feature_columns:
        beta = result.params.get(feature, np.nan)
        pct_change_for_1pp = (np.exp(beta * 0.01) - 1.0) * 100.0

        if pct_change_for_1pp < 0:
            direction = "csökkenti"
        elif pct_change_for_1pp > 0:
            direction = "növeli"
        else:
            direction = "nem változtatja"

        rows.append(
            {
                "target": target,
                "model_type": model_type,
                "feature": feature,
                "beta": beta,
                "estimated_pct_change_for_1pp": pct_change_for_1pp,
                "direction": direction,
                "p_value": result.pvalues.get(feature, np.nan),
            }
        )

    sensitivity_df = pd.DataFrame(rows)
    sensitivity_df["absolute_effect_rank"] = (
        sensitivity_df["estimated_pct_change_for_1pp"].abs()
        .rank(ascending=False, method="dense")
    )

    return sensitivity_df.sort_values("absolute_effect_rank")


def build_model_metrics(target: str, ols_result, glm_result, n_obs: int) -> pd.DataFrame:
    glm_pseudo_r2 = np.nan
    if glm_result.null_deviance and glm_result.null_deviance != 0:
        glm_pseudo_r2 = 1 - (glm_result.deviance / glm_result.null_deviance)

    return pd.DataFrame(
        [
            {
                "target": target,
                "model_type": "log_ols",
                "n_obs": n_obs,
                "aic": ols_result.aic,
                "bic": ols_result.bic,
                "rsquared": ols_result.rsquared,
                "rsquared_adj": ols_result.rsquared_adj,
                "deviance": np.nan,
                "null_deviance": np.nan,
                "pseudo_r2": np.nan,
            },
            {
                "target": target,
                "model_type": "gamma_glm",
                "n_obs": n_obs,
                "aic": glm_result.aic,
                "bic": np.nan,
                "rsquared": np.nan,
                "rsquared_adj": np.nan,
                "deviance": glm_result.deviance,
                "null_deviance": glm_result.null_deviance,
                "pseudo_r2": glm_pseudo_r2,
            },
        ]
    )


def save_text_summary(path: Path, result) -> None:
    path.write_text(str(result.summary()), encoding="utf-8")


def build_correlation_matrix(model_df: pd.DataFrame, target: str, feature_columns: list[str]) -> pd.DataFrame:
    corr_columns = feature_columns + [target]
    corr_df = model_df[corr_columns].corr(method="pearson")
    return corr_df


def run_univariate_gamma_glms(model_df: pd.DataFrame, target: str, feature_columns: list[str]) -> pd.DataFrame:
    rows = []

    for feature in feature_columns:
        X = sm.add_constant(model_df[[feature]], has_constant="add")
        y = model_df[target]

        model = sm.GLM(
            y,
            X,
            family=sm.families.Gamma(link=sm.families.links.Log())
        )
        result = model.fit()

        beta = result.params.get(feature, np.nan)
        p_value = result.pvalues.get(feature, np.nan)
        conf_int = result.conf_int()

        pct_change_for_1pp = (np.exp(beta * 0.01) - 1.0) * 100.0

        if pct_change_for_1pp < 0:
            direction = "csökkenti"
        elif pct_change_for_1pp > 0:
            direction = "növeli"
        else:
            direction = "nem változtatja"

        pseudo_r2 = np.nan
        if result.null_deviance and result.null_deviance != 0:
            pseudo_r2 = 1 - (result.deviance / result.null_deviance)

        rows.append(
            {
                "target": target,
                "feature": feature,
                "beta": beta,
                "p_value": p_value,
                "ci_lower": conf_int.loc[feature, 0],
                "ci_upper": conf_int.loc[feature, 1],
                "estimated_pct_change_for_1pp": pct_change_for_1pp,
                "direction": direction,
                "aic": result.aic,
                "deviance": result.deviance,
                "null_deviance": result.null_deviance,
                "pseudo_r2": pseudo_r2,
                "n_obs": len(model_df),
            }
        )

    return pd.DataFrame(rows).sort_values("p_value")


def run_for_target(df: pd.DataFrame, target: str, feature_columns: list[str]) -> dict:
    model_df = prepare_model_df(df, target, feature_columns)

    if len(model_df) < 10:
        raise ValueError(
            f"Túl kevés megfigyelés maradt a(z) {target} célváltozóhoz: {len(model_df)} sor."
        )

    ols_result, X_ols, _ = fit_log_ols(model_df, target, feature_columns)
    glm_result, _, _ = fit_gamma_glm(model_df, target, feature_columns)

    vif_df = calculate_vif(model_df, feature_columns)
    bp_df = calculate_breusch_pagan(ols_result, X_ols)

    coef_df = pd.concat(
        [
            build_coefficients_table(ols_result, target, "log_ols"),
            build_coefficients_table(glm_result, target, "gamma_glm"),
        ],
        ignore_index=True,
    )

    sensitivity_df = pd.concat(
        [
            build_sensitivity_table(ols_result, target, "log_ols", feature_columns),
            build_sensitivity_table(glm_result, target, "gamma_glm", feature_columns),
        ],
        ignore_index=True,
    )

    metrics_df = build_model_metrics(target, ols_result, glm_result, len(model_df))
    correlation_df = build_correlation_matrix(model_df, target, feature_columns)
    univariate_gamma_df = run_univariate_gamma_glms(model_df, target, feature_columns)

    return {
        "model_df": model_df,
        "ols_result": ols_result,
        "glm_result": glm_result,
        "vif_df": vif_df,
        "bp_df": bp_df,
        "coef_df": coef_df,
        "sensitivity_df": sensitivity_df,
        "metrics_df": metrics_df,
        "correlation_df": correlation_df,
        "univariate_gamma_df": univariate_gamma_df,
    }


def main() -> None:
    feature_columns = get_feature_columns()
    print("Regression run started.")
    print(f"Features: {feature_columns}")
    print(f"Primary target: {PRIMARY_TARGET}")
    print(f"Secondary target: {SECONDARY_TARGET}")

    df = load_regression_dataset()

    REGRESSION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    primary = run_for_target(df, PRIMARY_TARGET, feature_columns)
    secondary = run_for_target(df, SECONDARY_TARGET, feature_columns)

    primary["model_df"].to_csv(
        REGRESSION_OUTPUT_DIR / "primary_model_dataset.csv",
        index=False,
    )
    secondary["model_df"].to_csv(
        REGRESSION_OUTPUT_DIR / "secondary_model_dataset.csv",
        index=False,
    )

    save_text_summary(
        REGRESSION_OUTPUT_DIR / "primary_log_ols_summary.txt",
        primary["ols_result"],
    )
    save_text_summary(
        REGRESSION_OUTPUT_DIR / "primary_gamma_glm_summary.txt",
        primary["glm_result"],
    )
    save_text_summary(
        REGRESSION_OUTPUT_DIR / "secondary_log_ols_summary.txt",
        secondary["ols_result"],
    )
    save_text_summary(
        REGRESSION_OUTPUT_DIR / "secondary_gamma_glm_summary.txt",
        secondary["glm_result"],
    )

    pd.concat(
        [primary["coef_df"], secondary["coef_df"]],
        ignore_index=True,
    ).to_csv(REGRESSION_OUTPUT_DIR / "regression_coefficients.csv", index=False)

    pd.concat(
        [primary["sensitivity_df"], secondary["sensitivity_df"]],
        ignore_index=True,
    ).to_csv(REGRESSION_OUTPUT_DIR / "regression_sensitivity.csv", index=False)

    pd.concat(
        [primary["metrics_df"], secondary["metrics_df"]],
        ignore_index=True,
    ).to_csv(REGRESSION_OUTPUT_DIR / "regression_model_metrics.csv", index=False)

    primary["vif_df"].to_csv(REGRESSION_OUTPUT_DIR / "primary_vif.csv", index=False)
    secondary["vif_df"].to_csv(REGRESSION_OUTPUT_DIR / "secondary_vif.csv", index=False)

    primary["bp_df"].to_csv(REGRESSION_OUTPUT_DIR / "primary_breusch_pagan.csv", index=False)
    secondary["bp_df"].to_csv(REGRESSION_OUTPUT_DIR / "secondary_breusch_pagan.csv", index=False)

    primary["correlation_df"].to_csv(REGRESSION_OUTPUT_DIR / "primary_correlation_matrix.csv")
    secondary["correlation_df"].to_csv(REGRESSION_OUTPUT_DIR / "secondary_correlation_matrix.csv")

    primary["univariate_gamma_df"].to_csv(
        REGRESSION_OUTPUT_DIR / "primary_univariate_gamma_glm.csv",
        index=False,
    )
    secondary["univariate_gamma_df"].to_csv(
        REGRESSION_OUTPUT_DIR / "secondary_univariate_gamma_glm.csv",
        index=False,
    )

    run_metadata = {
        "features": feature_columns,
        "primary_target": PRIMARY_TARGET,
        "secondary_target": SECONDARY_TARGET,
        "primary_rows_used": int(len(primary["model_df"])),
        "secondary_rows_used": int(len(secondary["model_df"])),
    }

    (REGRESSION_OUTPUT_DIR / "run_metadata.json").write_text(
        json.dumps(run_metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nRegression finished successfully.")
    print(f"Outputs saved to: {REGRESSION_OUTPUT_DIR}")

    print("\nPrimary target model metrics:")
    print(primary["metrics_df"].to_string(index=False))

    print("\nSecondary target model metrics:")
    print(secondary["metrics_df"].to_string(index=False))

    print("\nPrimary sensitivity preview:")
    print(primary["sensitivity_df"].head(10).to_string(index=False))

    print("\nSecondary sensitivity preview:")
    print(secondary["sensitivity_df"].head(10).to_string(index=False))

    print("\nPrimary correlation matrix:")
    print(primary["correlation_df"].to_string())

    print("\nSecondary correlation matrix:")
    print(secondary["correlation_df"].to_string())

    print("\nPrimary univariate Gamma GLM preview:")
    print(primary["univariate_gamma_df"].to_string(index=False))

    print("\nSecondary univariate Gamma GLM preview:")
    print(secondary["univariate_gamma_df"].to_string(index=False))


if __name__ == "__main__":
    main()