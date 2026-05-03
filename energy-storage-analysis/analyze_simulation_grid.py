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

def load_stats():
    """Lädt alle Stats-Dateien und erstellt einen DataFrame."""
    stats_files = list(SIMULATED_DIR.glob("stats_*.txt"))
    
    data = []
    for f in stats_files:
        year, alpha, capacity = parse_stats_filename(f.name)
        if year is None:
            continue
        
        with open(f, 'r') as file:
            content = file.read()
            # Parse Stored und Loss
            stored_match = re.search(r'Stored: ([\d.]+)', content)
            loss_match = re.search(r'Loss: ([\d.]+)', content)
            
            if stored_match and loss_match:
                stored = float(stored_match.group(1))
                loss = float(loss_match.group(1))
                data.append({
                    'Year': year,
                    'Alpha': alpha,
                    'Capacity': capacity,
                    'Stored': stored,
                    'Loss': loss
                })
    
    return pd.DataFrame(data)

def create_plots(df):
    """Erstellt zwei Plots untereinander: Gespeichert und Verluste."""
    
    # Gruppiere nach Alpha und Capacity, berechne Mittelwert und Streuung
    grouped = df.groupby(['Alpha', 'Capacity']).agg({
        'Stored': ['mean', 'std', 'min', 'max'],
        'Loss': ['mean', 'std', 'min', 'max']
    }).reset_index()
    
    # Flatten column names
    grouped.columns = ['Alpha', 'Capacity', 
                       'Stored_mean', 'Stored_std', 'Stored_min', 'Stored_max',
                       'Loss_mean', 'Loss_std', 'Loss_min', 'Loss_max']
    
    # Erstelle Subplot Figure
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Gespeicherte Energie (TWh)', 'Verlust durch Effizienz (TWh)'),
        shared_xaxes=False,
        vertical_spacing=0.12
    )
    
    # Eindeutige Capacities für X-Achse
    capacities = sorted(grouped['Capacity'].unique())
    colors = {alpha: f"hsl({int(alpha*300)}, 70%, 50%)" for alpha in sorted(grouped['Alpha'].unique())}
    
    # Plot 1: Gespeicherte Energie
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
                legendgroup=f'alpha_{alpha}'
            ),
            row=1, col=1
        )
    
    # Plot 2: Verluste
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
                line=dict(color=colors[alpha]),
                showlegend=False,
                legendgroup=f'alpha_{alpha}'
            ),
            row=2, col=1
        )
    
    # Update Layout
    fig.update_xaxes(title_text="Speicherkapazität (TWh)", row=2, col=1)
    fig.update_xaxes(title_text="Speicherkapazität (TWh)", row=1, col=1)
    fig.update_yaxes(title_text="Gespeicherte Energie (TWh)", row=1, col=1)
    fig.update_yaxes(title_text="Verlust (TWh)", row=2, col=1)
    
    fig.update_layout(
        title_text="Energiespeicher-Analyse: Speicherung und Verluste",
        height=900,
        width=1200,
        hovermode='x unified',
        font=dict(size=12)
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
