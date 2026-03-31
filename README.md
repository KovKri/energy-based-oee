# Energy-Based OEE

Ez a projekt energiafogyasztás alapú OEE elemzéssel foglalkozik egy 5 tengelyes CNC gép példáján keresztül.

## Projekt célja

A cél a termelési és energiaadatok közös időalapú kezelése, majd ezek alapján:

- az OEE komponensekhez szükséges adatok modellezése,
- az energiafelhasználás állapotfüggő elemzése,
- a ciklusonkénti energiafogyasztás meghatározása,
- a darabra vetített energetikai mutatók számítása,
- valamint a későbbi KPI- és regressziós elemzés előkészítése.

A projekt referencia-gépe:

**DMG MORI DMU 50 3rd Generation**

## Főbb adatrétegek

A projekt adatmodellje három fő rétegre épül:

- **törzsadatok**  
  gép, művelet, állapotleképezés

- **nyers idősoros adatok**  
  energia-mérések, gépállapot-események, ciklusesemények

- **dúsított és számított adatok**  
  állapothoz és ciklushoz rendelt energiaadatok, ciklusenergia-összesítések, későbbi KPI-réteg

## Projektstruktúra

- `docs/` – dokumentáció
- `db/init/` – SQL inicializáló fájlok
- `db/seeds/` – generált CSV mintaadatok
- `scripts/` – Python szkriptek adatgeneráláshoz és adatbetöltéshez
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

## Technológia

- Python
- PostgreSQL + TimescaleDB
- Docker Desktop
- Git / GitHub