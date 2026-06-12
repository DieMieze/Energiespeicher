# Energy Storage Simulation

Dieses Projekt führt Energiespeicher-Simulationen für verschiedene Modellparameter durch und speichert die Ergebnisse für Analyse und Visualisierung.

## Projektstruktur

- `energy_storage_simulation.py` - Kernskript zur Ausführung einer Speichersimulation für ein gegebenes Jahr und Parameter-Set.
- `run_simulations_grid.py` - Wrapper zur Ausführung vieler Simulationen mit verschiedenen `alpha`- und `capacity`-Kombinationen.
- `analyze_simulation_grid.py` - Analysiert die generierten `stats_*.txt`-Dateien und erstellt eine zusammenfassende HTML-Visualisierung.
- `plot_simulation.py` - Erzeugt interaktive HTML-Plots für jede generierte Simulations-CSV-Datei.
- `storage.py` - Modelliert einen einzelnen Energiespeicher und dessen Zeitschritt-Logik.
- `storage_manager.py` - Verarbeitet mehrere Speicher in Reihenfolge der Effizienz und verteilt Überschuss / Defizit sequenziell.
- `data/raw/` - Hier müssen die Eingabedaten abgelegt werden.
- `data/simulated/` - Hier werden die Simulationsergebnisse, Statistiken und Analyseplots gespeichert.

## Benötigte Eingabedaten

Lege die Rohdaten im Ordner `data/raw/` ab.

### Erwartete Dateien

- Verbrauchsdaten:
  - `*Realisierter_Stromverbrauch*.csv`
  - Muss mindestens die Spalten `Datum von` und `Netzlast [MWh] Originalauflösungen` enthalten.
- Produktionsdaten:
  - `*Realisierte_Erzeugung*.csv`
  - Muss mindestens die Spalten `Datum von`, `Wind Offshore [MWh] Originalauflösungen`, `Wind Onshore [MWh] Originalauflösungen` und `Photovoltaik [MWh] Originalauflösungen` enthalten.

### Format

- Separator: `;`
- Dezimaltrenner: `,`
- Tausendertrennzeichen: `.`
- Datumsspalte: `Datum von`
- Die Daten werden nach Jahr gruppiert und Jahr-für-Jahr verarbeitet.

## Installation

Wechsle in das Projektverzeichnis und installiere die benötigten Python-Pakete.

```bash
cd energy-storage-analysis
python -m pip install pandas numpy plotly tqdm
```

> Hinweis: Das vorhandene `environment.yml` in diesem Ordner enthält aktuell Notebook-Inhalt und ist nicht als Conda-Umgebungskonfigurationsdatei nutzbar.

## Ausführen der Simulation

### Einzelne Simulation

```bash
python energy_storage_simulation.py --alpha 0.5 --capacity 0.11 --factor 1.05 --eta-in 0.9 --eta-out 0.9
```

Parameter:
- `--alpha`: Anteil der Photovoltaik an der erneuerbaren Produktion. `0.0` = nur Wind, `1.0` = nur PV.
- `--capacity`: Speicherkapazität in TWh.
- `--factor`: Multiplikator für das Produktionsziel (Basis 1000 TWh).
- `--eta-in`: Effizienz beim Laden des Speichers (0..1).
- `--eta-out`: Effizienz beim Entladen des Speichers (0..1).

### Grid-Simulationen mit vielen Parametern

```bash
python run_simulations_grid.py
```

Dieses Skript startet mehrere Simulationen für die definierten Werte in `ALPHAS` und `CAPACITIES` im oberen Bereich des Skripts.

## Ausgabe und Ergebnisse

### Simulationsergebnisse

Die Ergebnisse werden in `data/simulated/` abgelegt.

- `simulation_{year}_alpha_{alpha}_capacity_{capacity}.csv`
  - Zeitreihen mit Produktions-, Verbrauchs- und Speicherkennwerten.
- `stats_{year}_alpha_{alpha}_capacity_{capacity}.txt`
  - Zusammenfassende Kennzahlen wie Endfüllstand, Verluste, nicht speicherbarer Überschuss und ungedeckte Nachfrage.

### Analysen und Plots

- `data/simulated/analysis_grid.html`
  - Aggregierter Plot aus `analyze_simulation_grid.py`, der Verlust, gespeicherte Energie und Pumpspeicher-Durchsatz gegenüber Kapazität und `alpha` darstellt.
- `*.html`-Dateien, die von `plot_simulation.py` erzeugt werden.
  - Interaktive Zeitreihenplots für jede Simulation.

## Skripte im Überblick

### `energy_storage_simulation.py`

- Lädt Verbrauchs- und Produktionsdaten aus `data/raw/`.
- Normiert Verbrauch auf 1000 TWh pro Jahr.
- Skaliert die erneuerbare Produktion gemäß `alpha` und `factor`.
- Simuliert einen Pumpspeicher, einen chemischen Speicher und Wasserstoffspeicher.
- Berechnet Startfüllstände, führt einen zweiten Durchlauf durch und schreibt Ergebnisse in `data/simulated/`.

### `run_simulations_grid.py`

- Führt `energy_storage_simulation.py` wiederholt mit verschiedenen Kombinationen aus.
- Verwendet `tqdm` für eine Fortschrittsanzeige.
- Gibt am Ende fehlgeschlagene Kombinationen aus.

### `analyze_simulation_grid.py`

- Liest alle `stats_*.txt`-Dateien aus.
- Aggregiert nach `Alpha` und `Capacity`.
- Erstellt einen HTML-Plot der Kennzahlen.

### `plot_simulation.py`

- Liest alle `simulation_*.csv`-Dateien.
- Erzeugt für jede Datei einen interaktiven Plot als HTML.

## Neue Daten hinzufügen

1. Kopiere neue CSV-Dateien nach `data/raw/`.
2. Achte auf die korrekten Spaltennamen wie oben beschrieben.
3. Starte eine neue Simulation oder das Grid:
   - `python energy_storage_simulation.py ...`
   - oder `python run_simulations_grid.py`
4. Erzeuge anschließend die Analyse:
   - `python analyze_simulation_grid.py`
   - `python plot_simulation.py`

## Tipps

- Wenn du nur neue Jahre hinzufügen möchtest, kannst du die neuen Dateien unter `data/raw/` ablegen und erneut `run_simulations_grid.py` starten.
- Prüfe vor dem Start, dass `data/raw/` keine fehlerhaften CSV-Formate enthält.
- Passe bei Bedarf die Spaltennamen im Skript an, wenn deine Daten andere Feldnamen verwenden.

## Wichtige Orte

- Eingabedaten: `energy-storage-analysis/data/raw/`
- Simulationsergebnisse: `energy-storage-analysis/data/simulated/`
- Hauptskript: `energy-storage-analysis/energy_storage_simulation.py`
- Grid-Skript: `energy-storage-analysis/run_simulations_grid.py`
- Analyse: `energy-storage-analysis/analyze_simulation_grid.py`
- Plot-Erzeugung: `energy-storage-analysis/plot_simulation.py`
