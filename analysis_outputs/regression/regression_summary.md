# Regressziós összefoglaló

## Főmodell
- Célváltozó: `system_energy_per_good_part_kwh`
- Modell: `gamma_glm`
- Megfigyelések száma: 181
- Pseudo R²: 0.199140

### Szignifikáns hatások
- quality: koefficiens = -1.501085, p = 9.99139e-09, irány = csökkenti
- availability: koefficiens = -0.551285, p = 0.00658879, irány = csökkenti

## Másodlagos modell
- Célváltozó: `cycle_energy_per_good_part_kwh`
- Modell: `gamma_glm`
- Megfigyelések száma: 181
- Pseudo R²: 0.102072

### Szignifikáns hatások
- performance: koefficiens = -1.636061, p = 2.40816e-05, irány = csökkenti

## VIF
- availability: 1.017166
- performance: 1.022300
- quality: 1.008260