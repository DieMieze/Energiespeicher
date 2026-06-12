"""
Analysiere Simulationsergebnisse und erstelle Plots für Speicher und Verluste.
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
SIMULATED_DIR = BASE / "data" / "simulated"

def parse_stats_filename(filename):
    """Extrahiert Year, Alpha und Capacity aus dem Dateinamen."""
    # Format: stats_YYYY_alpha_X.X_capacity_YYYY.Y.txt
    filename = filename.replace('.txt', '')
    match = re.search(r'stats_(\d+)_alpha_([\d.]+)_capacity_([\d.]+)', filename)
    if match:
        return int(match.group(1)), float(match.group(2)), float(match.group(3))
    return None, None, None

def read_text_file(path):
    """Liest eine Textdatei zuerst als UTF-8, dann als CP1252, falls UTF-8 fehlschlägt."""
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return path.read_text(encoding='cp1252', errors='replace')

def load_stats():
    """Lädt alle Stats-Dateien und erstellt einen DataFrame."""
    stats_files = list(SIMULATED_DIR.glob("stats_*.txt"))
    
    data = []
    for f in stats_files:
        year, alpha, capacity = parse_stats_filename(f.name)
        if year is None:
            continue
        
        content = read_text_file(f)
        # Parse Stored und Loss (unterstützt Englisch und Deutsch)
        stored_match = re.search(r'(?:Stored|Gesamt-Endf(?:u|ü)llstand): ([\d.]+)', content)
        loss_match = re.search(r'(?:Loss|Gesamt-Verlust): ([\d.]+)', content)
        unstorable_match = re.search(r'Nicht gespeicherbarer (?:U|Ü)berschuss: ([\d.]+)', content)
        unmet_match = re.search(r'Ungedeckte Nachfrage: ([\d.]+)', content)
        
        # Parse Pumpspeicher-Daten
        pump_charge_match = re.search(r'Speicher: Pumpspeicher.*?Total charge: ([\d.]+)', content, re.DOTALL)
        pump_discharge_match = re.search(r'Speicher: Pumpspeicher.*?Total discharge: ([\d.]+)', content, re.DOTALL)
        pump_loss_match = re.search(r'Speicher: Pumpspeicher.*?Total loss: ([\d.]+)', content, re.DOTALL)
        
        if stored_match and loss_match:
            stored = float(stored_match.group(1))
            loss = float(loss_match.group(1))
            unstorable = float(unstorable_match.group(1)) if unstorable_match else 0.0
            unmet = float(unmet_match.group(1)) if unmet_match else 0.0
            pump_charge = float(pump_charge_match.group(1)) if pump_charge_match else 0.0
            pump_discharge = float(pump_discharge_match.group(1)) if pump_discharge_match else 0.0
            pump_loss = float(pump_loss_match.group(1)) if pump_loss_match else 0.0
            
            data.append({
                'Year': year,
                'Alpha': alpha,
                'Capacity': capacity,
                'Stored': stored,
                'Loss': loss,
                'Unstorable': unstorable,
                'Unmet': unmet,
                'PumpCharge': pump_charge,
                'PumpDischarge': pump_discharge,
                'PumpLoss': pump_loss
            })
    return pd.DataFrame(data)

def create_plots(df):
    """Erstellt Plots für Speicherung, Verluste und Pumpspeicher-Durchsatz."""
    
    # Gruppiere nach Alpha und Capacity, berechne Mittelwert und Streuung
    grouped = df.groupby(['Alpha', 'Capacity']).agg({
        'Stored': ['mean', 'std', 'min', 'max'],
        'Loss': ['mean', 'std', 'min', 'max'],
        'Unstorable': ['mean', 'std'],
        'Unmet': ['mean', 'std'],
        'PumpCharge': ['mean', 'std'],
        'PumpDischarge': ['mean', 'std'],
        'PumpLoss': ['mean', 'std']
    }).reset_index()
    
    # Flatten column names
    grouped.columns = ['Alpha', 'Capacity', 
                       'Stored_mean', 'Stored_std', 'Stored_min', 'Stored_max',
                       'Loss_mean', 'Loss_std', 'Loss_min', 'Loss_max',
                       'Unstorable_mean', 'Unstorable_std',
                       'Unmet_mean', 'Unmet_std',
                       'PumpCharge_mean', 'PumpCharge_std',
                       'PumpDischarge_mean', 'PumpDischarge_std',
                       'PumpLoss_mean', 'PumpLoss_std']
    
    # Erstelle Subplot Figure mit 3 Zeilen
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('Gesamtverlust (TWh) - HAUPTEFFEKT', 
                       'Gespeicherte Energie (TWh)',
                       'Pumpspeicher Durchsatz (TWh)'),
        shared_xaxes=True,
        vertical_spacing=0.1
    )
    
    colors = {alpha: f"hsl({int(alpha*300)}, 70%, 50%)" for alpha in sorted(grouped['Alpha'].unique())}
    
    # Plot 1: Gesamtverlust (HAUPTEFFEKT)
    for alpha in sorted(grouped['Alpha'].unique()):
        subset = grouped[grouped['Alpha'] == alpha].sort_values('Capacity')
        fig.add_trace(
            go.Scatter(
                x=subset['Capacity'],
                y=subset['Loss_mean'],
                error_y=dict(
                    type='data',
                    array=subset['Loss_std'],
                    visible=True
                ),
                mode='lines+markers',
                name=f'α={alpha}',
                line=dict(color=colors[alpha], width=3),
                marker=dict(size=8),
                legendgroup=f'alpha_{alpha}'
            ),
            row=1, col=1
        )
    
    # Plot 2: Gespeicherte Energie
    for alpha in sorted(grouped['Alpha'].unique()):
        subset = grouped[grouped['Alpha'] == alpha].sort_values('Capacity')
        fig.add_trace(
            go.Scatter(
                x=subset['Capacity'],
                y=subset['Stored_mean'],
                error_y=dict(
                    type='data',
                    array=subset['Stored_std'],
                    visible=True
                ),
                mode='lines+markers',
                name=f'α={alpha}',
                line=dict(color=colors[alpha]),
                showlegend=False,
                legendgroup=f'alpha_{alpha}'
            ),
            row=2, col=1
        )
    
    # Plot 3: Pumpspeicher Durchsatz (Charge + Discharge)
    for alpha in sorted(grouped['Alpha'].unique()):
        subset = grouped[grouped['Alpha'] == alpha].sort_values('Capacity')
        # Nutze Charge als Hauptindikator
        fig.add_trace(
            go.Scatter(
                x=subset['Capacity'],
                y=subset['PumpCharge_mean'],
                error_y=dict(
                    type='data',
                    array=subset['PumpCharge_std'],
                    visible=True
                ),
                mode='lines+markers',
                name=f'α={alpha} (Charge)',
                line=dict(color=colors[alpha], dash='solid'),
                showlegend=False,
                legendgroup=f'alpha_{alpha}'
            ),
            row=3, col=1
        )
    
    # Update Layout
    fig.update_xaxes(title_text="Speicherkapazität (TWh)", row=3, col=1)
    fig.update_yaxes(title_text="Verlust (TWh)", row=1, col=1)
    fig.update_yaxes(title_text="Speicher Level (TWh)", row=2, col=1)
    fig.update_yaxes(title_text="Pumpspeicher Charge (TWh)", row=3, col=1)
    
    fig.update_layout(
        title_text="Energiespeicher-Analyse: Haupteffekt Gesamtverlust",
        height=1200,
        width=1200,
        hovermode='x unified',
        font=dict(size=11)
    )
    
    return fig, grouped

def main():
    print("Lade Stats-Dateien...")
    df = load_stats()
    
    if df.empty:
        print("Keine Stats-Dateien gefunden!")
        return
    
    print(f"Gefunden: {len(df)} Datenpunkte über {df['Year'].nunique()} Jahre")
    print(f"Alphas: {sorted(df['Alpha'].unique())}")
    print(f"Capacities: {sorted(df['Capacity'].unique())}")
    
    fig, grouped = create_plots(df)
    
    # Speichere Plot
    output_file = BASE / "data" / "simulated" / "analysis_grid.html"
    fig.write_html(output_file)
    print(f"\nPlot gespeichert: {output_file}")
    
    # Gebe Summary aus
    print("\nZusammenfassung (Mittelwerte über alle Jahre):")
    print(grouped.to_string(index=False))

if __name__ == "__main__":
    main()
