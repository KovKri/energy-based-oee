# Regressziós értelmezési kontextus

A projekt célja az OEE és az energiaintenzitás kapcsolatának vizsgálata ipari környezetben.

## Célváltozók

### Elsődleges célváltozó
`system_energy_per_good_part_kwh`

Jelentése:
az adott időszak teljes rendszerenergia-fogyasztása osztva a jó darabok számával.

Ez tartalmazza:
- a termelő ciklusok energiáját
- a nem termelő energiafogyasztást
- az álló, nem termelő energiafogyasztást is

Ezért közvetlenül kapcsolódik a rejtett energiaveszteség fogalmához.

### Másodlagos célváltozó
`cycle_energy_per_good_part_kwh`

Jelentése:
a jó darabokhoz tartozó ciklusenergia osztva a jó darabok számával.

Ez inkább a közvetlen gyártási ciklusok energetikai viselkedését tükrözi.

## Magyarázó változók

### availability
rendelkezésre állás

### performance
teljesítmény

### quality
minőség

## Modellek

### Főmodell
Gamma GLM log linkkel

### Kontrollmodell
log-transzformált OLS

## Értelmezési szabályok

- Negatív együttható azt jelenti, hogy a változó növekedése csökkenti az energiaintenzitást.
- Pozitív együttható azt jelenti, hogy a változó növekedése növeli az energiaintenzitást.
- Egy hatást csak akkor tekintünk erős következtetésnek, ha statisztikailag szignifikáns.
- Az alacsony VIF azt jelenti, hogy a magyarázó változók között nincs érdemi multikollinearitás.
- A rendszer szintű célváltozó esetén a nem termelő veszteségek is megjelennek.
- A ciklusalapú célváltozó esetén inkább a közvetlen gyártási folyamat hatásai dominálnak.

## Elvárt stílus

A modell értelmezése:
- legyen magyar nyelvű
- legyen szakmai, de közérthető
- ne találjon ki új számokat
- külön emelje ki a főmodell és a másodlagos modell tanulságát
- külön jelezze, ha egy változó nem szignifikáns