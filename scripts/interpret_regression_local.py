import json
import os
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
REGRESSION_DIR = BASE_DIR / "analysis_outputs" / "regression"
RAG_CONTEXT_DIR = BASE_DIR / "rag" / "context"

SUMMARY_PATH = REGRESSION_DIR / "regression_summary.json"
OUTPUT_JSON_PATH = REGRESSION_DIR / "regression_local_llm_interpretation.json"
OUTPUT_MD_PATH = REGRESSION_DIR / "regression_local_llm_interpretation.md"
OUTPUT_FILTERED_INPUT_PATH = REGRESSION_DIR / "regression_llm_filtered_input.json"


def load_summary() -> dict:
    if not SUMMARY_PATH.exists():
        raise FileNotFoundError(
            f"Nem található a regressziós összefoglaló: {SUMMARY_PATH}\n"
            "Előbb futtasd: python scripts/build_regression_summary.py"
        )

    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    summary.pop("draft_key_messages", None)
    return summary


def load_rag_context() -> str:
    if not RAG_CONTEXT_DIR.exists():
        return ""

    parts = []
    for path in sorted(RAG_CONTEXT_DIR.glob("*.md")):
        parts.append(f"\n\n# Forrásfájl: {path.name}\n")
        parts.append(path.read_text(encoding="utf-8"))

    return "\n".join(parts).strip()


def select_effect_rows(rows: list[dict]) -> dict:
    significant = [r for r in rows if r.get("is_significant") is True]
    non_significant = [r for r in rows if r.get("is_significant") is False]

    return {
        "significant_effects": significant,
        "non_significant_effects": non_significant,
    }


def build_filtered_llm_input(summary: dict) -> dict:
    primary = summary["primary_model"]
    secondary = summary["secondary_model"]

    primary_effects = select_effect_rows(primary["sensitivity"])
    secondary_effects = select_effect_rows(secondary["sensitivity"])

    filtered = {
        "significance_level": summary["significance_level"],
        "allowed_feature_names": ["availability", "performance", "quality"],
        "interpretation_constraints": {
            "do_not_introduce_new_variables": True,
            "do_not_infer_new_business_concepts": True,
            "do_not_claim_causality_beyond_model_results": True,
            "only_significant_results_may_be_used_as_main_conclusions": True,
            "non_significant_results_must_be_marked_as_uncertain": True,
        },
        "primary_model": {
            "target": primary["target"],
            "model_type": primary["model_type"],
            "metrics": {
                "n_obs": primary["metrics"]["n_obs"],
                "pseudo_r2": primary["metrics"]["pseudo_r2"],
                "aic": primary["metrics"]["aic"],
            },
            "significant_effects": primary_effects["significant_effects"],
            "non_significant_effects": primary_effects["non_significant_effects"],
        },
        "secondary_model": {
            "target": secondary["target"],
            "model_type": secondary["model_type"],
            "metrics": {
                "n_obs": secondary["metrics"]["n_obs"],
                "pseudo_r2": secondary["metrics"]["pseudo_r2"],
                "aic": secondary["metrics"]["aic"],
            },
            "significant_effects": secondary_effects["significant_effects"],
            "non_significant_effects": secondary_effects["non_significant_effects"],
        },
        "vif": summary["vif"],
    }

    return filtered


def build_prompt(filtered_summary: dict, rag_context: str) -> str:
    return f"""
Te egy ipari OEE- és energiahatékonysági szakértő vagy.

Feladat:
A megadott regressziós eredményeket magyar nyelven, szakszerűen és tömören értelmezd.

SZIGORÚ SZABÁLYOK:
- kizárólag a megadott adatokból dolgozz
- ne találj ki új változónevet, új mutatót vagy új üzleti fogalmat
- csak ezekről a változókról beszélhetsz: availability, performance, quality
- ne írj olyan állítást, amely nincs benne a strukturált regressziós eredményben
- ha egy hatás nem szignifikáns, azt egyértelműen bizonytalanként kezeld
- fő következtetést csak szignifikáns hatásból vonj le
- ne használj marketing stílust
- ne ismételd vissza feleslegesen a teljes inputot
- a válasz legyen teljes egészében magyar nyelvű

További fontos szabály:
- ha valamire nincs elég bizonyíték az inputban, akkor ezt írd: "erre a modell alapján nincs elég bizonyíték"
- ne használj olyan kifejezést, ami nincs az inputban vagy a projektkontextusban
- ne írj olyat, hogy "rendezési idő", "arányos", "okozza", ha ez nincs kifejezetten alátámasztva

Projektkontextus:
{rag_context}

Strukturált regressziós input:
{json.dumps(filtered_summary, ensure_ascii=False, indent=2)}

A válasz pontos szerkezete legyen ez:

## Rövid összefoglaló
2-4 mondat.

## Főmodell értelmezése
- írd le, melyik szignifikáns tényezők fontosak
- írd le, mely tényezők nem szignifikánsak
- írd le röviden, mit jelent ez a célváltozóra

## Másodlagos modell értelmezése
- írd le, melyik szignifikáns tényező fontos
- írd le, mely tényezők nem szignifikánsak
- írd le röviden, mit jelent ez a célváltozóra

## Megbízhatósági megjegyzések
- írj a VIF-ről
- írj röviden arról, hogy a nem szignifikáns eredményeket óvatosan kell kezelni

## 3 kulcskövetkeztetés
Pontosan 3 számozott pont.
Mindegyik csak az inputban szereplő, alátámasztott állítást tartalmazhat.
""".strip()


def call_ollama(prompt: str) -> str:
    load_dotenv()

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
    timeout_sec = int(os.getenv("OLLAMA_TIMEOUT_SEC", "1800"))

    url = f"{base_url.rstrip('/')}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout_sec) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data["response"]


def save_outputs(filtered_summary: dict, prompt: str, interpretation: str) -> None:
    OUTPUT_FILTERED_INPUT_PATH.write_text(
        json.dumps(filtered_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    payload = {
        "provider": "ollama",
        "summary_file": str(SUMMARY_PATH),
        "filtered_input_file": str(OUTPUT_FILTERED_INPUT_PATH),
        "prompt": prompt,
        "interpretation": interpretation,
    }

    OUTPUT_JSON_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    OUTPUT_MD_PATH.write_text(
        interpretation,
        encoding="utf-8",
    )


def main() -> None:
    summary = load_summary()
    rag_context = load_rag_context()
    filtered_summary = build_filtered_llm_input(summary)
    prompt = build_prompt(filtered_summary, rag_context)
    interpretation = call_ollama(prompt)
    save_outputs(filtered_summary, prompt, interpretation)

    print("Local LLM interpretation finished successfully.")
    print(f"Filtered input JSON: {OUTPUT_FILTERED_INPUT_PATH}")
    print(f"JSON output: {OUTPUT_JSON_PATH}")
    print(f"Markdown output: {OUTPUT_MD_PATH}")
    print("\nGenerated interpretation preview:\n")
    print(interpretation)


if __name__ == "__main__":
    main()