from typing import Optional, Dict, List

DEFAULT_INITIAL_LEVEL_PERCENT = 0.0


class Storage:
    """Ein Energiespeicher mit Lade-/Entladeeffizienz und reduzierten Mismatch-Berechnungen."""

    def __init__(self, name: str, capacity_twh: float, eta_in: float = 1.0, eta_out: float = 1.0, initial_level_percent: Optional[float] = None):
        self.name = name
        self.capacity_twh = float(capacity_twh)
        self.eta_in = float(eta_in)
        self.eta_out = float(eta_out)
        init_percent = DEFAULT_INITIAL_LEVEL_PERCENT if initial_level_percent is None else float(initial_level_percent)
        self.level_twh = init_percent * self.capacity_twh
        self.reduced_mismatch: List[float] = []
        self.power_flow: List[float] = []
        self.loss_history: List[float] = []
        self.charge_history: List[float] = []
        self.discharge_history: List[float] = []
        self.total_charged = 0.0
        self.total_discharged = 0.0
        self.total_loss = 0.0

    @property
    def roundtrip_efficiency(self) -> float:
        return self.eta_in * self.eta_out

    def _positive_part(self, value: float) -> float:
        return max(value, 0.0)

    def _negative_part(self, value: float) -> float:
        return max(-value, 0.0)

    def timestep(self, delta_twh: float) -> Dict[str, float]:
        """Verarbeitet einen Zeitschritt mit Delta = Produktion - Last.

        Liefert ein Ergebnisdikt mit reduziertem Mismatch, Powerflow, Füllstand und Verlust zurück.
        """
        # Änderung der Speichermenge
        if delta_twh >= 0.0:
            max_charge = self.capacity_twh - self.level_twh
            f = min(delta_twh * self.eta_in, max_charge)
        else:
            max_discharge = self.level_twh
            f = max(delta_twh / self.eta_out, -max_discharge)

        f_plus = self._positive_part(f)
        f_minus = self._negative_part(f)
        f_tilde = f_plus / self.eta_in - f_minus * self.eta_out # Powerflow in/aus dem Speicher
        self.power_flow.append(f_tilde)

        self.level_twh += f
        self.level_twh = max(0.0, min(self.level_twh, self.capacity_twh))

        step_loss = 0.0
        if f > 0.0:
            self.total_charged += f
            step_loss = f / self.eta_in - f
            self.total_loss += step_loss
        elif f < 0.0:
            self.total_discharged += -f
            step_loss = (-f) * (1.0 - self.eta_out)
            self.total_loss += step_loss

        delta_r = delta_twh - f_tilde
        self.reduced_mismatch.append(delta_r)
        self.loss_history.append(step_loss)
        self.charge_history.append(f_plus)
        self.discharge_history.append(f_minus)

        return {
            "delta_r": delta_r,
            "f_tilde": f_tilde,
            "storage_level": self.level_twh,
            "storage_level_percent": self.get_level_percent(),
            "step_loss": step_loss,
            "charge_twh": f_plus,
            "discharge_twh": f_minus,
        }

    def get_level(self) -> float:
        return self.level_twh

    def get_level_percent(self) -> float:
        return 100.0 * self.level_twh / self.capacity_twh

    def get_last_reduced_mismatch(self) -> Optional[float]:
        return self.reduced_mismatch[-1] if self.reduced_mismatch else None

    def reset(self, initial_level_percent: Optional[float] = None) -> None:
        init_percent = DEFAULT_INITIAL_LEVEL_PERCENT if initial_level_percent is None else float(initial_level_percent)
        self.level_twh = init_percent * self.capacity_twh
        self.reduced_mismatch.clear()
        self.power_flow.clear()
        self.loss_history.clear()
        self.charge_history.clear()
        self.discharge_history.clear()
        self.total_charged = 0.0
        self.total_discharged = 0.0
        self.total_loss = 0.0
