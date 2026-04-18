import pandas as pd
import numpy as np
from pathlib import Path
import sys

# --- Projektstruktur ---
try:
    BASE = Path(__file__).resolve().parent
except NameError:
    BASE = Path.cwd()

RAW_DIR = BASE / "data" / "raw"
OUTPUT_DIR = BASE / "data" / "simulated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Benutzerdefinierte Variablen ---
FAKTOR = 1.0  # Faktor für Produktionsnormalisierung (1000 TWh * FAKTOR)
ALPHA = 0.5  # Verhältnis Sonne zu Wind (z.B. 0.5 bedeutet 50% Sonne, 50% Wind)
SPEICHER_KAPAZITAET_TWH = 10000.0  # Speicherkapazität in TWh
EINSPEISE_EFFIZIENZ = 1  # Effizienz beim Einspeisen (90%)
AUSSPEISE_EFFIZIENZ = 1  # Effizienz beim Ausspeisen (90%)

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

def simulate_storage(production_twh, consumption_twh, capacity_twh, eta_in, eta_out):
    """Simuliert den Speicher mit Produktion und Verbrauch."""
    storage_level = 0.5 * capacity_twh  # Start bei 50% Kapazität
    storage_levels = []
    deltas = []
    total_stored = 0.0

    for prod, cons in zip(production_twh, consumption_twh):
        delta = prod - cons
        if delta > 0:
            # Überschuss: Einspeisen
            to_store = delta * eta_in
            if storage_level + to_store <= capacity_twh:
                storage_level += to_store
                total_stored += to_store
            else:
                # Speicher voll, überschüssige Energie geht verloren
                storage_level = capacity_twh
                total_stored += (capacity_twh - (storage_level - to_store))
        elif delta < 0:
            # Defizit: Ausspeisen
            needed = -delta / eta_out
            if storage_level >= needed:
                storage_level -= needed
            else:
                # Speicher leer, Defizit bleibt
                storage_level = 0.0
        deltas.append(delta)
        storage_levels.append(storage_level)

    return storage_levels, deltas, total_stored

def main():
    print("Lade Verbrauchsdaten...")
    cons_df = load_consumption_data()
    if cons_df.empty:
        print("Keine Verbrauchsdaten gefunden.")
        return

    print("Lade Produktionsdaten...")
    prod_df = load_production_data()
    if prod_df.empty:
        print("Keine Produktionsdaten gefunden.")
        return

    # Verfügbare Jahre
    years = sorted(cons_df["Jahr"].dropna().unique())
    print(f"Verfügbare Jahre: {years}")

    for year in years:
        print(f"\n--- Verarbeite Jahr {year} ---")

        # Filter Daten für Jahr
        cons_y = cons_df[cons_df["Jahr"] == year].copy()
        prod_y = prod_df[prod_df["Jahr"] == year].copy()

        if cons_y.empty or prod_y.empty:
            print(f"Keine Daten für Jahr {year}.")
            continue

        # Parse Zahlen
        cons_y[CONSUMPTION_COL] = parse_german_number_series(cons_y[CONSUMPTION_COL])
        prod_y[WIND_OFFSHORE_COL] = parse_german_number_series(prod_y.get(WIND_OFFSHORE_COL, pd.Series()))
        prod_y[WIND_ONSHORE_COL] = parse_german_number_series(prod_y.get(WIND_ONSHORE_COL, pd.Series()))
        prod_y[PV_COL] = parse_german_number_series(prod_y.get(PV_COL, pd.Series()))

        # Kombiniere Wind
        wind_total = prod_y[WIND_OFFSHORE_COL].fillna(0) + prod_y[WIND_ONSHORE_COL].fillna(0)

        # Normiere Produktion: Nur Wind und Sonne, Verhältnis alpha
        pv_annual = prod_y[PV_COL].sum() / 4.0
        wind_annual = wind_total.sum() / 4.0
        total_renew = pv_annual + wind_annual

        if total_renew > 0:
            # Skaliere auf 1000 TWh * FAKTOR, mit Verhältnis alpha
            target_prod = 1000.0 * FAKTOR
            pv_scaled = target_prod * ALPHA
            wind_scaled = target_prod * (1 - ALPHA)

            # Normiere die Zeitreihen
            prod_y["PV_norm_TWh"] = rescale_to_target(prod_y[PV_COL], pv_scaled)
            prod_y["Wind_norm_TWh"] = rescale_to_target(wind_total, wind_scaled)
            prod_y["Prod_total_norm_TWh"] = prod_y["PV_norm_TWh"] + prod_y["Wind_norm_TWh"]
        else:
            prod_y["PV_norm_TWh"] = 0
            prod_y["Wind_norm_TWh"] = 0
            prod_y["Prod_total_norm_TWh"] = 0

        # Normiere Verbrauch auf 1000 TWh
        cons_y["Cons_norm_TWh"] = rescale_to_target(cons_y[CONSUMPTION_COL], 1000.0)

        # Simuliere Speicher
        prod_series = prod_y["Prod_total_norm_TWh"]
        cons_series = cons_y["Cons_norm_TWh"]

        # Sortiere nach Zeit
        prod_y = prod_y.sort_values("Datum von")
        cons_y = cons_y.sort_values("Datum von")
        prod_series = prod_y["Prod_total_norm_TWh"]
        cons_series = cons_y["Cons_norm_TWh"]

        storage_levels, deltas, total_stored = simulate_storage(
            prod_series, cons_series, SPEICHER_KAPAZITAET_TWH, EINSPEISE_EFFIZIENZ, AUSSPEISE_EFFIZIENZ
        )

        # Ergebnisse speichern
        results_df = pd.DataFrame({
            DATE_COL: prod_y[DATE_COL],
            "Prod_norm_TWh": prod_y["Prod_total_norm_TWh"],
            "Cons_norm_TWh": cons_y["Cons_norm_TWh"],
            "Delta_TWh": deltas,
            "Storage_Level_TWh": storage_levels
        })

        output_file = OUTPUT_DIR / f"simulation_{year}_alpha_{ALPHA}_capacity_{SPEICHER_KAPAZITAET_TWH}.csv"
        results_df.to_csv(output_file, sep=";", decimal=",", index=False)

        print(f"Jahr {year}: Gespeichert {total_stored:.2f} TWh, Ergebnisse in {output_file}")

    print("\nSimulation abgeschlossen.")

if __name__ == "__main__":
    main()