"""
Wrapper-Skript zur Ausführung von Energiespeicher-Simulationen mit verschiedenen Parameterkombinationen.
"""
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
SIM_SCRIPT = BASE / "energy_storage_simulation.py"

# Parameter Grid
ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0]  # 0 = nur Wind, 1 = nur Sonne
CAPACITIES = [10.0, 50.0, 100.0, 500.0, 1000.0, 5000.0]  # TWh
FAKTOR = 1.0
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
        f"--capacity={capacity}",
        f"--factor={FAKTOR}",
        f"--eta-in={EINSPEISE_EFFIZIENZ}",
        f"--eta-out={AUSSPEISE_EFFIZIENZ}"
    ], cwd=BASE)

    return result.returncode == 0


def main():
    total = len(ALPHAS) * len(CAPACITIES)
    completed = 0

    for alpha in ALPHAS:
        for capacity in CAPACITIES:
            if run_simulation(alpha, capacity):
                completed += 1
            print(f"\nFortschritt: {completed}/{total}")

    print(f"\n{'='*60}")
    print(f"Alle Simulationen abgeschlossen: {completed}/{total} erfolgreich")
    print(f"{'='*60}")
    print("\nNächster Schritt: Führe 'python analyze_simulation_grid.py' aus")


if __name__ == "__main__":
    main()
