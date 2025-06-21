import pandas as pd

# Dateipfade
verbrauch_path = "Realisierter_Stromverbrauch_202401010000_202501010000_Viertelstunde.csv"
preise_path = "Gro_handelspreise_202401010000_202501010000_Stunde.csv"
produktion_path = "Realisierte_Erzeugung_202401010000_202501010000_Viertelstunde.csv"

# ggf. dritten Dateipfad ergänzen: dritte_datei_path = "..."

# Einlesen der Viertelstunden-Daten
verbrauch = pd.read_csv(
    verbrauch_path,
    sep=';',
    decimal=',',
    parse_dates=['Datum von', 'Datum bis'],
    dayfirst=True
)

# Einlesen der Stundenpreise
produktion = pd.read_csv(
    produktion_path,
    sep=';',
    decimal=',',
    parse_dates=['Datum von', 'Datum bis'],
    dayfirst=True
)

# Einlesen der Stundenpreise
preise = pd.read_csv(
    preise_path,
    sep=';',
    decimal=',',
    parse_dates=['Datum von', 'Datum bis'],
    dayfirst=True
)

# Beispiel: Zeige die ersten Zeilen
print("Verbrauchsdaten:")
print(verbrauch.head())
print("\nPreisdaten:")
print(preise.head())