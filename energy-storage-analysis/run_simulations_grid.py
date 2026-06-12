"""
Wrapper-Skript zur Ausführung von Energiespeicher-Simulationen mit verschiedenen Parameterkombinationen.
"""
import subprocess
import sys
from pathlib import Path
from tqdm import tqdm

BASE = Path(__file__).resolve().parent
SIM_SCRIPT = BASE / "energy_storage_simulation.py"

ALREADY_INSTALLED = 0.01

# Parameter Grid
ALPHAS = [0.4, 0.45, 0.5, 0.55, 0.6]  # 0 = nur Wind, 1 = nur Sonne
CAPACITIES = [0, 0.100,0.270,0.48, 4] # TWh
FAKTOR = 1.05
EINSPEISE_EFFIZIENZ = 0.9
AUSSPEISE_EFFIZIENZ = 0.9


def run_simulation(alpha, capacity):
    """Führt die Simulation mit gegebenen Parametern aus."""
    print(f"\n{'='*60}")
    print(f"Starte Simulation: ALPHA={alpha}, CAPACITY={capacity} TWh")
    print(f"{'='*60}")

    result = subprocess.run([
        sys.executable,
        str(SIM_SCRIPT),
        f"--alpha={alpha}",
        f"--capacity={capacity + ALREADY_INSTALLED}",
        f"--factor={FAKTOR}",
        f"--eta-in={EINSPEISE_EFFIZIENZ}",
        f"--eta-out={AUSSPEISE_EFFIZIENZ}"
    ], cwd=BASE, capture_output=True)

    return result.returncode == 0


def main():
    # Erzeuge alle Parameterkombinationen
    simulations = [(alpha, capacity) for alpha in ALPHAS for capacity in CAPACITIES]
    total = len(simulations)
    
    print(f"Starte {total} Simulationen...")
    print(f"ALPHAS: {ALPHAS}")
    print(f"CAPACITIES: {CAPACITIES}")
    print(f"\n{'='*60}\n")
    
    completed = 0
    failed = []
    
    # Mit Ladebalken
    with tqdm(simulations, desc="Simulationen", unit="sim", ncols=80) as pbar:
        for alpha, capacity in pbar:
            pbar.set_description(f"α={alpha}, Cap={capacity} TWh")
            if run_simulation(alpha, capacity):
                completed += 1
            else:
                failed.append((alpha, capacity))
            pbar.update(0)  # Progress wird durch Iterator aktualisiert

    print(f"\n{'='*60}")
    print(f"Alle Simulationen abgeschlossen: {completed}/{total} erfolgreich")
    if failed:
        print(f"Fehlgeschlagen: {len(failed)}")
        for alpha, capacity in failed:
            print(f"  - α={alpha}, Cap={capacity} TWh")
    print(f"{'='*60}")
    print("\nNächster Schritt: Führe 'python analyze_simulation_grid.py' aus")


if __name__ == "__main__":
    main()
