from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .scenarios import WaterInventory


@dataclass(frozen=True)
class WaterState:
    temperature_k: float
    vapor_quality: float
    liquid_mass_kg_per_m: float
    steam_mass_kg_per_m: float
    sensible_energy_j_per_m: float
    latent_energy_j_per_m: float
    superheat_energy_j_per_m: float
    phase: str


def water_state_from_energy(
    energy_added_j_per_m: float,
    water: WaterInventory,
) -> WaterState:
    """Переводит накопленную энергию в состояние воды или пара."""
    energy = max(float(energy_added_j_per_m), 0.0)
    mass = water.mass_kg_per_m
    if mass <= 0.0:
        return WaterState(
            temperature_k=water.initial_temperature_k,
            vapor_quality=0.0,
            liquid_mass_kg_per_m=0.0,
            steam_mass_kg_per_m=0.0,
            sensible_energy_j_per_m=0.0,
            latent_energy_j_per_m=0.0,
            superheat_energy_j_per_m=0.0,
            phase="no_water",
        )

    heat_to_saturation = mass * water.cp_liquid_j_kg_k * max(
        water.saturation_temperature_k - water.initial_temperature_k,
        0.0,
    )
    heat_to_evaporate = mass * water.latent_heat_j_kg

    if energy < heat_to_saturation:
        temperature = water.initial_temperature_k + energy / (
            mass * water.cp_liquid_j_kg_k
        )
        return WaterState(
            temperature_k=temperature,
            vapor_quality=0.0,
            liquid_mass_kg_per_m=mass,
            steam_mass_kg_per_m=0.0,
            sensible_energy_j_per_m=energy,
            latent_energy_j_per_m=0.0,
            superheat_energy_j_per_m=0.0,
            phase="liquid_heating",
        )

    after_saturation = energy - heat_to_saturation
    if after_saturation < heat_to_evaporate:
        vapor_quality = after_saturation / heat_to_evaporate
        steam_mass = vapor_quality * mass
        return WaterState(
            temperature_k=water.saturation_temperature_k,
            vapor_quality=vapor_quality,
            liquid_mass_kg_per_m=mass - steam_mass,
            steam_mass_kg_per_m=steam_mass,
            sensible_energy_j_per_m=heat_to_saturation,
            latent_energy_j_per_m=after_saturation,
            superheat_energy_j_per_m=0.0,
            phase="boiling",
        )

    superheat = after_saturation - heat_to_evaporate
    temperature = water.saturation_temperature_k + superheat / (
        mass * water.cp_vapor_j_kg_k
    )
    return WaterState(
        temperature_k=temperature,
        vapor_quality=1.0,
        liquid_mass_kg_per_m=0.0,
        steam_mass_kg_per_m=mass,
        sensible_energy_j_per_m=heat_to_saturation,
        latent_energy_j_per_m=heat_to_evaporate,
        superheat_energy_j_per_m=superheat,
        phase="steam_superheating",
    )


def water_energy_for_temperature_j_per_m(
    temperature_k: float,
    water: WaterInventory,
) -> float:
    """Возвращает энергию воды/пара при полном испарении выше насыщения."""
    mass = water.mass_kg_per_m
    if mass <= 0.0:
        return 0.0
    temperature = max(float(temperature_k), water.initial_temperature_k)
    heat_to_saturation = mass * water.cp_liquid_j_kg_k * max(
        water.saturation_temperature_k - water.initial_temperature_k,
        0.0,
    )
    if temperature <= water.saturation_temperature_k:
        return mass * water.cp_liquid_j_kg_k * (
            temperature - water.initial_temperature_k
        )
    return (
        heat_to_saturation
        + mass * water.latent_heat_j_kg
        + mass * water.cp_vapor_j_kg_k * (temperature - water.saturation_temperature_k)
    )


def vectorized_water_state(
    energy_added_j_per_m: np.ndarray,
    water: WaterInventory,
) -> dict[str, np.ndarray]:
    """Считает состояние воды или пара для временного ряда энергии."""
    states = [water_state_from_energy(energy, water) for energy in energy_added_j_per_m]
    return {
        "water_temperature_k": np.array([state.temperature_k for state in states]),
        "vapor_quality": np.array([state.vapor_quality for state in states]),
        "liquid_mass_kg_per_m": np.array(
            [state.liquid_mass_kg_per_m for state in states]
        ),
        "steam_mass_kg_per_m": np.array([state.steam_mass_kg_per_m for state in states]),
        "water_sensible_energy_j_per_m": np.array(
            [state.sensible_energy_j_per_m for state in states]
        ),
        "water_latent_energy_j_per_m": np.array(
            [state.latent_energy_j_per_m for state in states]
        ),
        "water_superheat_energy_j_per_m": np.array(
            [state.superheat_energy_j_per_m for state in states]
        ),
        "water_phase": np.array([state.phase for state in states]),
    }
