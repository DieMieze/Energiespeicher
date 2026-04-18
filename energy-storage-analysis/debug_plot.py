import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent
SIMULATED_DIR = BASE / "data" / "simulated"

# Lade erste Simulationsdatei
files = list(SIMULATED_DIR.glob("simulation_*.csv"))
if files:
    f = files[0]
    print(f"Analysiere: {f.name}")
    df = pd.read_csv(f, sep=";", decimal=",")
    
    print(f"\nGesamtzeilen in CSV: {len(df)}")
    print(f"Spalten: {df.columns.tolist()}")
    
    print(f"\nErste 5 Zeilen von 'Datum von':")
    print(df["Datum von"].head(10))
    
    print(f"\nDatentyp 'Datum von': {df['Datum von'].dtype}")
    print(f"\nUnique Werte in 'Datum von': {df['Datum von'].nunique()}")
    print(f"Duplicate 'Datum von': {df['Datum von'].duplicated().sum()}")
    
    # Parse das Datum
    df["Datum von"] = pd.to_datetime(df["Datum von"], dayfirst=False, errors='coerce')
    df_clean = df.dropna(subset=["Datum von"])
    
    print(f"\nNach Parsing und Dropna:")
    print(f"Zeilen: {len(df_clean)}")
    print(f"Unique Datum+Uhrzeit: {df_clean['Datum von'].nunique()}")
    
    print(f"\nErste 5 Zeilen nach Parsing:")
    print(df_clean[["Datum von", "Prod_norm_TWh", "Cons_norm_TWh"]].head())
    
    print(f"\nLast 5 Zeilen nach Parsing:")
    print(df_clean[["Datum von", "Prod_norm_TWh", "Cons_norm_TWh"]].tail())
