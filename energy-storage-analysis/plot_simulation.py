import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

# --- Projektstruktur ---
BASE = Path(__file__).resolve().parent
SIMULATED_DIR = BASE / "data" / "simulated"

def extract_params(filename):
    """Extrahiert alpha und capacity aus dem Dateinamen."""
    # Entferne .csv
    filename = filename.replace('.csv', '')
    parts = filename.split('_')
    if len(parts) >= 6 and parts[2] == 'alpha' and parts[4] == 'capacity':
        try:
            alpha = float(parts[3])
            capacity = float(parts[5])
            return alpha, capacity
        except ValueError:
            pass
    return None, None

def plot_simulation(file_path):
    """Plottet Prod, Cons und Delta gegen Zeit mit Plotly."""
    df = pd.read_csv(file_path, sep=";", decimal=",")
    df["Datum von"] = pd.to_datetime(df["Datum von"], dayfirst=False, errors='coerce')

    # Entferne Zeilen mit ungültigen Daten
    df = df.dropna(subset=["Datum von"])

    # Einheiten: Von TWh pro 15 min zu TW (Leistung)
    # 15 min = 0.25 h, also TW = TWh / 0.25
    df["Prod_TW"] = df["Prod_norm_TWh"] / 0.25
    df["Cons_TW"] = df["Cons_norm_TWh"] / 0.25
    df["Delta_TW"] = df["Delta_TWh"] / 0.25

    # Extrahiere Parameter
    filename = file_path.name
    alpha, capacity = extract_params(filename)
    if alpha is None:
        alpha = "unbekannt"
        capacity = "unbekannt"

    # Plotly Figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Datum von"], y=df["Prod_TW"], mode='lines', name='Produktion (TW)', line=dict(width=1)))
    fig.add_trace(go.Scatter(x=df["Datum von"], y=df["Cons_TW"], mode='lines', name='Verbrauch (TW)', line=dict(width=1)))
    fig.add_trace(go.Scatter(x=df["Datum von"], y=df["Delta_TW"], mode='lines', name='Delta (Prod - Cons) (TW)', line=dict(width=1)))

    fig.update_layout(
        title=f"Simulation: Alpha={alpha}, Capacity={capacity} TWh",
        xaxis_title="Zeit",
        yaxis_title="Leistung (TW)",
        width=1500,  # Breit für bessere Auflösung
        height=600
    )

    # Speichere als HTML (interaktiv)
    plot_file = file_path.with_suffix('.html')
    fig.write_html(plot_file)
    print(f"Interaktiver Plot gespeichert: {plot_file}")

def main():
    files = list(SIMULATED_DIR.glob("simulation_*.csv"))
    if not files:
        print("Keine Simulationsdateien gefunden.")
        return

    for f in files:
        print(f"Verarbeite: {f.name}")
        plot_simulation(f)

    print("Alle interaktiven Plots erstellt.")

if __name__ == "__main__":
    main()