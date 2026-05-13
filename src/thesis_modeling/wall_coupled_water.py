from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .scenarios import Scenario
from .water_state import (
    vectorized_water_state,
    water_energy_for_temperature_j_per_m,
    water_state_from_energy,
)


SIGMA_SB_W_M2_K4 = 5.670374419e-8


@dataclass(frozen=True)
class WallHeatTransfer:
    liquid_htc_w_m2_k: float = 3.0e4
    boiling_htc_w_m2_k: float = 8.0e4
    steam_htc_w_m2_k: float = 5.0e3
    wall_emissivity: float = 0.35
    max_substep_s: float = 1.0e-3


def apply_wall_coupled_water_model(
    result: dict[str, Any],
    scenario: Scenario,
    heat_transfer: WallHeatTransfer | None = None,
) -> dict[str, Any]:
    """Считает воду у ТВЭЛа только через поток от наружной стенки."""
    model = heat_transfer or WallHeatTransfer(
        liquid_htc_w_m2_k=scenario.water.heat_transfer_coefficient_w_m2_k,
    )
    time_s = np.asarray(result["time_s"], dtype=float)
    wall_temperature_k = np.asarray(result["clad_outer_k"], dtype=float)
    area_m2_per_m = 2.0 * np.pi * scenario.geometry.clad_outer_radius_m

    water_energy = np.zeros_like(time_s, dtype=float)
    heat_flux = np.zeros_like(time_s, dtype=float)
    htc = np.zeros_like(time_s, dtype=float)
    cap_active = np.zeros_like(time_s, dtype=bool)

    for index in range(1, time_s.size):
        energy = float(water_energy[index - 1])
        dt = float(time_s[index] - time_s[index - 1])
        steps = max(1, int(np.ceil(dt / max(model.max_substep_s, 1e-9))))
        sub_dt = dt / steps
        wall_k = float(wall_temperature_k[index])
        last_flux = 0.0
        last_htc = 0.0
        limited = False
        for _ in range(steps):
            state = water_state_from_energy(energy, scenario.water)
            delta_t = max(wall_k - state.temperature_k, 0.0)
            last_htc = _effective_htc_w_m2_k(model, state.phase, wall_k, state.temperature_k)
            last_flux = last_htc * delta_t
            energy += last_flux * area_m2_per_m * sub_dt

            cap_energy = water_energy_for_temperature_j_per_m(wall_k, scenario.water)
            if energy > cap_energy:
                energy = cap_energy
                limited = True
        water_energy[index] = max(energy, water_energy[index - 1])
        heat_flux[index] = last_flux
        htc[index] = last_htc
        cap_active[index] = limited

    updated = dict(result)
    if "water_temperature_k" in updated:
        updated["genfoam_coolant_temperature_k"] = np.asarray(
            updated["water_temperature_k"],
            dtype=float,
        )
    updated["water_energy_j_per_m"] = water_energy
    updated["wall_heat_flux_w_m2"] = heat_flux
    updated["wall_heat_transfer_htc_w_m2_k"] = htc
    updated["wall_temperature_cap_active"] = cap_active
    updated["thermal_adapter"] = "wall_coupled_annular_water"
    updated.update(vectorized_water_state(water_energy, scenario.water))
    updated["energy_residual_j_per_m"] = (
        np.asarray(updated["pulse_energy_j_per_m"], dtype=float)
        - np.asarray(updated["fuel_energy_j_per_m"], dtype=float)
        - np.asarray(updated["clad_energy_j_per_m"], dtype=float)
        - water_energy
    )
    return updated


def _effective_htc_w_m2_k(
    model: WallHeatTransfer,
    phase: str,
    wall_temperature_k: float,
    water_temperature_k: float,
) -> float:
    if phase == "liquid_heating":
        base = model.liquid_htc_w_m2_k
    elif phase == "boiling":
        base = model.boiling_htc_w_m2_k
    else:
        base = model.steam_htc_w_m2_k
    return base + _radiation_linear_htc(
        model.wall_emissivity,
        wall_temperature_k,
        water_temperature_k,
    )


def _radiation_linear_htc(
    emissivity: float,
    wall_temperature_k: float,
    water_temperature_k: float,
) -> float:
    if wall_temperature_k <= water_temperature_k:
        return 0.0
    return (
        max(emissivity, 0.0)
        * SIGMA_SB_W_M2_K4
        * (wall_temperature_k**2 + water_temperature_k**2)
        * (wall_temperature_k + water_temperature_k)
    )
