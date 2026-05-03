import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import sys

from storage_manager import StorageManager

# --- Projektstruktur ---
try:
    BASE = Path(__file__).resolve().parent
except NameError:
    BASE = Path.cwd()

RAW_DIR = BASE / "data" / "raw"
OUTPUT_DIR = BASE / "data" / "simulated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Benutzerdefinierte Variablen ---
# FAKTOR = 1.0  # Faktor für Produktionsnormalisierung (1000 TWh * FAKTOR)
# ALPHA = 0.5  # Verhältnis Sonne zu Wind (z.B. 0.5 bedeutet 50% Sonne, 50% Wind)
# SPEICHER_KAPAZITAET_TWH = 10000.0  # Speicherkapazität in TWh
# EINSPEISE_EFFIZIENZ = 1  # Effizienz beim Einspeisen (90%)
# AUSSPEISE_EFFIZIENZ = 1  # Effizienz beim Ausspeisen (90%)

# --- Spaltennamen ---
DATE_COL = "Datum von"
CONSUMPTION_COL = "Netzlast [MWh] Originalauflösungen"
WIND_OFFSHORE_COL = "Wind Offshore [MWh] Originalauflösungen"
WIND_ONSHORE_COL = "Wind Onshore [MWh] Originalauflösungen"
PV_COL = "Photovoltaik [MWh] Originalauflösungen"

def parse_german_number_series(s: pd.Series) -> pd.Series:
    """Konvertiert deutsche Zahlenformate (Punkte als Tausendertrenner, Komma als Dezimaltrenner) in float."""
    s = s.fillna("").astype(str).str.strip()
    s = s.str.replace(r'\.(?=\d{3}(?:[.\s]\d{3})*(?:,|$))', '', regex=True)
    s = s.str.replace(',', '.', regex=False)
    s = s.replace('', np.nan)
    return pd.to_numeric(s, errors='coerce')

def load_consumption_data():
    """Lädt Verbrauchsdaten aus CSV-Dateien."""
    files = sorted(RAW_DIR.glob("*Realisierter_Stromverbrauch*.csv"))
    dfs = []
    for f in files:
        df = pd.read_csv(f, sep=";", dtype=str, low_memory=False, encoding='utf-8')
        df[DATE_COL] = pd.to_datetime(df[DATE_COL], dayfirst=True, errors='coerce')
        df["Jahr"] = df[DATE_COL].dt.year
        df["source_file"] = f.name
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def load_production_data():
    """Lädt Produktionsdaten aus CSV-Dateien."""
    files = sorted(RAW_DIR.glob("*Realisierte_Erzeugung*.csv"))
    dfs = []
    for f in files:
        df = pd.read_csv(f, sep=";", dtype=str, low_memory=False, encoding='utf-8')
        df[DATE_COL] = pd.to_datetime(df[DATE_COL], dayfirst=True, errors='coerce')
        df["Jahr"] = df[DATE_COL].dt.year
        df["source_file"] = f.name
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def rescale_to_target(series, target_twh=1000.0):
    """Normiert eine Serie auf 1000 TWh pro Jahr."""
    annual_sum = series.sum()  
    if annual_sum > 0:
        return series * (target_twh / annual_sum)
    return series


def prepare_yearly_series(cons_y, prod_y, alpha, factor):
    cons_y[CONSUMPTION_COL] = parse_german_number_series(cons_y[CONSUMPTION_COL])
    prod_y[WIND_OFFSHORE_COL] = parse_german_number_series(prod_y.get(WIND_OFFSHORE_COL, pd.Series(dtype='float64')))
    prod_y[WIND_ONSHORE_COL] = parse_german_number_series(prod_y.get(WIND_ONSHORE_COL, pd.Series(dtype='float64')))
    prod_y[PV_COL] = parse_german_number_series(prod_y.get(PV_COL, pd.Series(dtype='float64')))

    wind_total = prod_y[WIND_OFFSHORE_COL].fillna(0) + prod_y[WIND_ONSHORE_COL].fillna(0)
    total_renew = prod_y[PV_COL].sum() / 4.0 + wind_total.sum() / 4.0

    if total_renew > 0:
        target_prod = 1000.0 * factor
        prod_y["PV_norm_TWh"] = rescale_to_target(prod_y[PV_COL], target_prod * alpha)
        prod_y["Wind_norm_TWh"] = rescale_to_target(wind_total, target_prod * (1 - alpha))
        prod_y["Prod_total_norm_TWh"] = prod_y["PV_norm_TWh"] + prod_y["Wind_norm_TWh"]
    else:
        prod_y["PV_norm_TWh"] = 0
        prod_y["Wind_norm_TWh"] = 0
        prod_y["Prod_total_norm_TWh"] = 0

    cons_y["Cons_norm_TWh"] = rescale_to_target(cons_y[CONSUMPTION_COL], 1000.0)
    prod_y = prod_y.sort_values(DATE_COL)
    cons_y = cons_y.sort_values(DATE_COL)
    return prod_y["Prod_total_norm_TWh"], cons_y["Cons_norm_TWh"], prod_y, cons_y


def build_storage_manager(storage_defs, initial_level_percents=None):
    manager = StorageManager()
    for name, capacity, eta_in, eta_out in storage_defs:
        initial_level_percent = None
        if initial_level_percents and name in initial_level_percents:
            initial_level_percent = initial_level_percents[name]
        manager.add_speicher(name, capacity, eta_in, eta_out, initial_level_percent)
    return manager


def run_storage_simulation(production_twh, consumption_twh, storage_manager):
    rows = []
    for prod, cons in zip(production_twh, consumption_twh):
        delta = prod - cons
        delta_r_final, step_results = storage_manager.timestep(delta)
        row = {
            "Delta_TWh": delta,
            "Delta_r_final_TWh": delta_r_final,
        }

        for storage_result in step_results:
            name = storage_result["name"]
            row[f"Delta_r_{name}_TWh"] = storage_result["delta_r"]
            row[f"Storage_Level_{name}_TWh"] = storage_result["storage_level"]
            row[f"Storage_Level_{name}_Pct"] = storage_result["storage_level_percent"]
            row[f"Loss_{name}_TWh"] = storage_result["step_loss"]
            row[f"Power_Flow_{name}_TWh"] = storage_result["f_tilde"]
            row[f"Charge_{name}_TWh"] = storage_result["charge_twh"]
            row[f"Discharge_{name}_TWh"] = storage_result["discharge_twh"]

        rows.append(row)

    return storage_manager, rows


""" def simulate_storage(production_twh, consumption_twh, capacity_twh, eta_in, eta_out):
    # Simuliert den Speicher mit Produktion und Verbrauch.
    # Gibt zurück: storage_levels, deltas, total_stored, total_loss
    storage_level = 0.5 * capacity_twh  # Start bei 50% Kapazität
    storage_levels = []
    deltas = []
    total_stored = 0.0
    total_loss = 0.0

    for prod, cons in zip(production_twh, consumption_twh):
        delta = prod - cons
        if delta > 0:
            # Überschuss: Einspeisen
            energy_to_store = delta  # Energie vor Effizienzberechnung
            stored_energy = energy_to_store * eta_in  # Energie nach Effizienz
            loss_on_charging = energy_to_store * (1 - eta_in)  # Verlust beim Laden
            
            if storage_level + stored_energy <= capacity_twh:
                storage_level += stored_energy
                total_stored += stored_energy
                total_loss += loss_on_charging
            else:
                # Speicher voll, überschüssige Energie geht verloren
                total_loss += (capacity_twh - storage_level) * (1 - eta_in)/eta_in
                storage_level = capacity_twh
                total_stored += (capacity_twh - storage_level)
        elif delta < 0:
            # Defizit: Ausspeisen
            energy_needed = -delta  # Energie, die gebraucht wird
            energy_from_storage = energy_needed / eta_out  # Energie aus Speicher (mit Verlust)
            loss_on_discharging = energy_needed * (1 - eta_out)  # Verlust beim Entladen
            
            if storage_level >= energy_from_storage:
                storage_level -= energy_from_storage
                total_loss += loss_on_discharging
            else:
                # Speicher leer, Defizit bleibt
                total_loss += (energy_from_storage - storage_level) * (1 - eta_out)
                storage_level = 0.0
        deltas.append(delta)
        storage_levels.append(storage_level)

    return storage_levels, deltas, total_stored, total_loss """

def main():
    parser = argparse.ArgumentParser(description='Speichersimulation mit variablen Parametern')
    parser.add_argument('--alpha', type=float, default=0.5, help='Anteil PV an erneuerbarer Produktion (0..1)')
    parser.add_argument('--capacity', type=float, default=1000.0, help='Speicherkapazität in TWh')
    parser.add_argument('--factor', type=float, default=1.0, help='Multiplikator für Produktionsziel (1000 TWh * factor)')
    parser.add_argument('--eta-in', type=float, default=1, help='Einspeiseeffizienz (0..1)')
    parser.add_argument('--eta-out', type=float, default=1, help='Ausspeiseeffizienz (0..1)')
    args = parser.parse_args()

    ALPHA = args.alpha
    SPEICHER_KAPAZITAET_TWH = args.capacity
    FAKTOR = args.factor
    EINSPEISE_EFFIZIENZ = args.eta_in
    AUSSPEISE_EFFIZIENZ = args.eta_out

    print(f"Lade Verbrauchsdaten...")
    cons_df = load_consumption_data()
    if cons_df.empty:
        print("Keine Verbrauchsdaten gefunden.")
        return

    print(f"Lade Produktionsdaten...")
    prod_df = load_production_data()
    if prod_df.empty:
        print("Keine Produktionsdaten gefunden.")
        return

    # Verfügbare Jahre
    years = sorted(cons_df["Jahr"].dropna().unique())
    print(f"Verfügbare Jahre: {years}")
    end_levels_by_storage = {}
    capacities_by_storage = {}
    yearly_data = []

    for year in years:
        print(f"\n--- Verarbeite Jahr {year} ---")

        # Filter Daten für Jahr
        cons_y = cons_df[cons_df["Jahr"] == year].copy()
        prod_y = prod_df[prod_df["Jahr"] == year].copy()

        if cons_y.empty or prod_y.empty:
            print(f"Keine Daten für Jahr {year}.")
            continue

        # Normiere Verbrauch auf 1000 TWh
        prod_series, cons_series, prod_y, cons_y = prepare_yearly_series(cons_y, prod_y, ALPHA, FAKTOR)

        storage_defs = [("Speicher_1", SPEICHER_KAPAZITAET_TWH, EINSPEISE_EFFIZIENZ, AUSSPEISE_EFFIZIENZ)]
        manager = build_storage_manager(storage_defs)
        manager, _ = run_storage_simulation(prod_series, cons_series, manager)

        for storage in manager.storages:
            end_levels_by_storage.setdefault(storage.name, []).append(storage.get_level())
            capacities_by_storage[storage.name] = storage.capacity_twh

        yearly_data.append((year, prod_series, cons_series, prod_y, cons_y))

    initial_level_percents = {}
    for name, levels in end_levels_by_storage.items():
        capacity = capacities_by_storage.get(name)
        initial_level_percents[name] = float(np.mean(levels)) / capacity if capacity > 0 else 0.0
        initial_level_percents[name] = max(0.0, min(initial_level_percents[name], 1.0))

    print("Startfüllstände für den zweiten Durchgang:")
    for name, percent in initial_level_percents.items():
        print(f"  {name}: {percent * 100:.1f}%")

    for year, prod_series, cons_series, prod_y, cons_y in yearly_data:
        manager.reset(initial_level_percents)
        manager, step_rows = run_storage_simulation(prod_series, cons_series, manager)

        results_df = pd.DataFrame(step_rows)
        results_df[DATE_COL] = prod_y[DATE_COL].reset_index(drop=True)
        results_df["Prod_norm_TWh"] = prod_y["Prod_total_norm_TWh"].reset_index(drop=True)
        results_df["Cons_norm_TWh"] = cons_y["Cons_norm_TWh"].reset_index(drop=True)

        output_file = OUTPUT_DIR / f"simulation_{year}_alpha_{ALPHA}_capacity_{SPEICHER_KAPAZITAET_TWH}.csv"
        results_df.to_csv(output_file, sep=";", decimal=",", index=False)

        stats_file = OUTPUT_DIR / f"stats_{year}_alpha_{ALPHA}_capacity_{SPEICHER_KAPAZITAET_TWH}.txt"
        with open(stats_file, 'w') as f:
            f.write(f"Jahr: {year}\n")
            f.write(f"Alpha: {ALPHA}\n")
            f.write(f"Capacity: {SPEICHER_KAPAZITAET_TWH} TWh\n")
            f.write(f"Gesamt-Endfüllstand: {sum(storage.get_level() for storage in manager.storages):.4f} TWh\n")
            f.write(f"Gesamt-Verlust: {sum(storage.total_loss for storage in manager.storages):.4f} TWh\n")
            for storage in manager.storages:
                f.write(f"\nSpeicher: {storage.name}\n")
                f.write(f"  Startfüllstand: {initial_level_percents[storage.name] * storage.capacity_twh:.4f} TWh ({initial_level_percents[storage.name] * 100:.1f}%)\n")
                f.write(f"  Endfüllstand: {storage.get_level():.4f} TWh ({storage.get_level_percent():.1f}%)\n")
                f.write(f"  Total charge: {storage.total_charged:.4f} TWh\n")
                f.write(f"  Total discharge: {storage.total_discharged:.4f} TWh\n")
                f.write(f"  Total loss: {storage.total_loss:.4f} TWh\n")

        print(f"Jahr {year}: Gesamt-Endfüllstand {sum(storage.get_level() for storage in manager.storages):.4f} TWh, Gesamt-Verlust {sum(storage.total_loss for storage in manager.storages):.4f} TWh")

    print("\nSimulation abgeschlossen.")

if __name__ == "__main__":
    main()