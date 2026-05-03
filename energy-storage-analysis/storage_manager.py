from typing import Optional, Dict, List, Tuple

from storage import Storage


class StorageManager:
    """Verwalter für mehrere Speicher; sortiert nach Roundtrip-Effizienz und verarbeitet Timesteps sequentiell."""

    def __init__(self):
        self.storages: List[Storage] = []
        self.final_reduced_mismatch: List[float] = []

    def add_speicher(
        self,
        name: str,
        capacity_twh: float,
        eta_in: float,
        eta_out: float,
        initial_level_percent: Optional[float] = None,
    ) -> Storage:
        storage = Storage(name, capacity_twh, eta_in, eta_out, initial_level_percent)
        self.storages.append(storage)
        self.sort_speicher()
        return storage

    def sort_speicher(self) -> None:
        self.storages.sort(key=lambda s: s.roundtrip_efficiency, reverse=True)

    def timestep(self, delta_twh: float) -> Tuple[float, List[Dict[str, float]]]:
        current_delta = delta_twh
        step_results: List[Dict[str, float]] = []
        for storage in self.storages:
            storage_result = storage.timestep(current_delta)
            step_results.append({"name": storage.name, **storage_result})
            current_delta = storage_result["delta_r"]

        self.final_reduced_mismatch.append(current_delta)
        return current_delta, step_results

    def reset(self, initial_levels: Optional[Dict[str, float]] = None) -> None:
        for storage in self.storages:
            initial_level = None
            if initial_levels and storage.name in initial_levels:
                initial_level = initial_levels[storage.name]
            storage.reset(initial_level)
        self.final_reduced_mismatch.clear()

    def get_storage_names(self) -> List[str]:
        return [storage.name for storage in self.storages]
