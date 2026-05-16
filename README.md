# Energy-Based OEE

Ez a projekt energiafogyasztás alapú OEE elemzéssel foglalkozik egy 5 tengelyes CNC gép példáján keresztül.

## Projekt célja

A cél a termelési és energiaadatok közös időalapú kezelése, majd ezek alapján:

- az OEE komponensekhez szükséges adatok modellezése,
- az energiafelhasználás állapotfüggő elemzése,
- a ciklusonkénti energiafogyasztás meghatározása,
- a darabra vetített energetikai mutatók számítása,
- valamint a KPI- és regressziós elemzés előkészítése.

A projekt referencia-gépe:

**DMG MORI DMU 50 3rd Generation**

## Főbb adatrétegek

A projekt adatmodellje három fő rétegre épül:

- **törzsadatok**  
  gép, művelet, állapotleképezés

- **nyers idősoros adatok**  
  energia-mérések, gépállapot-események, ciklusesemények

- **dúsított és számított adatok**  
  állapothoz és ciklushoz rendelt energiaadatok, ciklusenergia-összesítések, KPI- és regressziós réteg

## Projektstruktúra

- `docs/` – dokumentáció
- `db/init/` – SQL inicializáló és migration fájlok
- `db/seeds/` – generált CSV mintaadatok
- `scripts/` – Python szkriptek adatgeneráláshoz, betöltéshez, regresszióhoz és dashboard publikáláshoz
- `analysis_outputs/` – generált regressziós outputok
- `grafana/dashboards/` – exportált Grafana dashboard definíciók
- `tests/` – célzott pytest tesztek
- `notebooks/` – későbbi elemző notebookok

## Főbb adatbázis-táblák

- `machine`
- `operation`
- `state_mapping`
- `energy_measurement`
- `machine_state_event`
- `cycle_event`
- `energy_enriched`
- `cycle_energy_summary`
- `regression_dashboard_summary`

## Technológia

- Python
- PostgreSQL + TimescaleDB
- Docker Desktop
- Grafana
- Git / GitHub

## Környezet beállítása

### 1. Python virtuális környezet

Windows PowerShell / Command Prompt esetén:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux / macOS esetén:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Környezeti változók

Hozz létre egy `.env` fájlt a `.env.example` alapján.


### 3. Konténerek indítása

```bash
docker compose up -d
```

## Futtatási sorrend

```bash
python scripts/load_data.py
python scripts/build_enriched.py
python scripts/validate_kpis.py
python scripts/prepare_regression_input.py
python scripts/run_regression.py
python scripts/build_regression_summary.py
python scripts/publish_regression_to_dashboard.py
```

### Ha új mintaadatokat is generálni szeretnél ezt futtasd le először

```bash
python scripts/generate_data.py
```

## Mit csinálnak a főbb scriptek?

### `generate_data.py`

Demo célú mintaadatokat generál CSV fájlokba.

### `load_data.py`

A seed CSV fájlokat betölti az adatbázisba.

### `build_enriched.py`

Újraépíti az `energy_enriched` és `cycle_energy_summary` réteget.

### `validate_kpis.py`

Ellenőrzi a fő energetikai és ciklusalapú KPI-kat.

### `prepare_regression_input.py`

Előkészíti a regressziós inputot a `regression_base_hourly` nézetből.

### `run_regression.py`

Lefuttatja a regressziós modelleket és elmenti az eredményeket.

### `build_regression_summary.py`

Strukturált JSON és Markdown összefoglalót készít a regressziós kimenetekből.

### `publish_regression_to_dashboard.py`

Felhasználóbarát regressziós összefoglalót publikál adatbázisba, ahonnan a Grafana olvassa.

## Regressziós pipeline röviden

A regressziós elemzés célja annak vizsgálata, hogy az OEE komponensek hogyan hatnak az energiaintenzitásra.

Két célváltozó szerepel:

- `system_energy_per_good_part_kwh`  
  Teljes rendszerenergia / jó darab. Ez tartalmazza a nem termelő veszteségeket is.

- `cycle_energy_per_good_part_kwh`  
  Ciklusenergia / jó darab. Ez inkább a közvetlen gyártási ciklus energiaigényét mutatja.

A fő modell:

- Gamma GLM

A kontrollmodell:

- log-OLS

A pipeline fő artifactjai:

```text
analysis_outputs/regression_base_hourly.csv
analysis_outputs/regression_input_aggregated.csv
analysis_outputs/regression_input_metadata.json
analysis_outputs/regression/primary_model_dataset.csv
analysis_outputs/regression/secondary_model_dataset.csv
analysis_outputs/regression/regression_model_metrics.csv
analysis_outputs/regression/regression_coefficients.csv
analysis_outputs/regression/regression_sensitivity.csv
analysis_outputs/regression/regression_summary.json
analysis_outputs/regression/regression_summary.md
```

## Dashboard / Grafana

A Grafana a számított adatokat és a regressziós összefoglalókat közvetlenül az adatbázisból olvassa.

A regressziós dashboard szövegek nem LLM-ből származnak, hanem szabályalapúan készülnek a `regression_summary.json` alapján a `publish_regression_to_dashboard.py` segítségével.

A projekt tartalmaz egy exportált Grafana dashboard definíciót is:

- `grafana/dashboards/energy_oee_dashboard.json`

### Dashboard importálása

1. Indítsd el a konténereket:

```bash
docker compose up -d
```

2. Nyisd meg a Grafanát:

```text
http://localhost:3000/
```

3. Ellenőrizd, hogy a PostgreSQL datasource elérhető:

```text
Név: Energy OEE DB
```

4. Importáld a dashboardot:

```text
Grafana → Dashboards → New → Import
```

5. Válaszd ki az exportált dashboard fájlt:

```text
grafana/dashboards/energy_oee_dashboard.json
```

6. Datasource-nak válaszd ki:

```text
Energy OEE DB
```

7. Import után a dashboard közvetlenül ezen a linken érhető el:

```text
http://localhost:3000/d/adr79sk/energy-oee-dashboard
```

## Tesztek

A projekt tartalmaz célzott pytest teszteket is:

```bash
pytest tests -q
```

Külön is futtathatók például:

```bash
pytest tests/test_load_data.py -q
pytest tests/test_prepare_regression_input.py -q
pytest tests/test_cycle_boundary.py -q
```

## Fontos migration / init megjegyzés

A `db/init/` mappában lévő SQL fájlok Docker alatt automatikusan csak az első adatbázis-inicializáláskor futnak le.

Ez azt jelenti, hogy ha egy meglévő DB volume-ot használsz, akkor az újonnan hozzáadott init / migration fájlok nem fognak automatikusan lefutni.


### Lehetséges megoldások

#### 1. Régi volume törlése és tiszta indulás

```bash
docker compose down -v
docker compose up -d
```

#### 2. Kézi futtatás a meglévő adatbázison

Példa:

```bash
docker exec -i energy_oee_db psql -U energy_user -d energy_oee -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/007_regression_dashboard_sensitivity.sql
```

Ha később külön index vagy constraint SQL fájlokat adsz hozzá, azok kézzel is futtathatók hasonló módon:

```bash
docker exec -i energy_oee_db psql -U energy_user -d energy_oee -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/008_indexes.sql
docker exec -i energy_oee_db psql -U energy_user -d energy_oee -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/009_constraints.sql
```

## Ismert korlátok

- Az energiaallokáció jelenleg mintapont-alapú közelítést használ. A `delta_energy_kwh` érték a két mérési pont közötti energiafelhasználást reprezentálja, de a hozzárendelés jelenleg az aktuális mintapont időbélyege alapján történik.
- A dashboardot kiszolgáló aggregációk jelenleg normál SQL view-kra épülnek. Production környezetben ezek TimescaleDB continuous aggregate formában is megvalósíthatók.
- Az állapotlogika egy része még SQL oldali szabályokra támaszkodik, ezért további általánosítás későbbi refaktorálási lehetőség.

## Rövid összegzés

A projekt egy rétegezett, reprodukálható adatpipeline-t valósít meg, amely:

- összerendeli a termelési és energiaadatokat közös időalapon,
- kiszámítja az energetikai és OEE-alapú KPI-kat,
- regressziós elemzéssel vizsgálja az OEE komponensek energiaintenzitásra gyakorolt hatását,
- és az eredményeket Grafana dashboardon is megjeleníthető formában publikálja.