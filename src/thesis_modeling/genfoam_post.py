from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .scenarios import Scenario
from .water_state import vectorized_water_state


def pulse_energy_series_j_per_m(time_s: np.ndarray, scenario: Scenario) -> np.ndarray:
    """Возвращает накопленную энергию прямоугольного импульса."""
    pulse = scenario.pulse
    if pulse.shape != "square":
        raise ValueError(f"Неподдерживаемая форма импульса: {pulse.shape}")
    if pulse.duration_s <= 0.0:
        return np.zeros_like(time_s, dtype=float)
    active_time_s = np.clip(time_s, 0.0, pulse.duration_s)
    return pulse.energy_j_per_m * active_time_s / pulse.duration_s


def integrate_wall_heat_flux_j_per_m(
    time_s: np.ndarray,
    heat_flux_w_m2: np.ndarray,
    scenario: Scenario,
) -> np.ndarray:
    """Интегрирует поток через наружную поверхность оболочки на метр твэла."""
    outer_area_m2_per_m = 2.0 * np.pi * scenario.geometry.clad_outer_radius_m
    power_w_per_m = heat_flux_w_m2 * outer_area_m2_per_m
    energy_j_per_m = np.zeros_like(time_s, dtype=float)
    if time_s.size > 1:
        energy_j_per_m[1:] = np.cumsum(
            0.5
            * (power_w_per_m[1:] + power_w_per_m[:-1])
            * np.diff(time_s)
        )
    return np.maximum(energy_j_per_m, 0.0)


def water_energy_from_temperature_j_per_m(
    water_temperature_k: np.ndarray,
    scenario: Scenario,
) -> np.ndarray:
    """Оценивает энергию пара по температуре, если GeN-Foam не выгрузил поток."""
    water = scenario.water
    mass_kg_per_m = water.mass_kg_per_m
    if mass_kg_per_m <= 0.0:
        return np.zeros_like(water_temperature_k, dtype=float)

    heat_to_saturation = (
        mass_kg_per_m
        * water.cp_liquid_j_kg_k
        * max(water.saturation_temperature_k - water.initial_temperature_k, 0.0)
    )
    heat_to_evaporate = mass_kg_per_m * water.latent_heat_j_kg

    energy = np.empty_like(water_temperature_k, dtype=float)
    below_saturation = water_temperature_k <= water.saturation_temperature_k
    energy[below_saturation] = (
        mass_kg_per_m
        * water.cp_liquid_j_kg_k
        * np.maximum(
            water_temperature_k[below_saturation] - water.initial_temperature_k,
            0.0,
        )
    )
    energy[~below_saturation] = (
        heat_to_saturation
        + heat_to_evaporate
        + mass_kg_per_m
        * water.cp_vapor_j_kg_k
        * (water_temperature_k[~below_saturation] - water.saturation_temperature_k)
    )
    return np.maximum(energy, 0.0)


def canonicalize_thermal_series(
    columns: Mapping[str, Any],
    scenario: Scenario,
    *,
    source: str,
    provenance: str | Path | None = None,
) -> dict[str, Any]:
    """Приводит выгрузку GeN-Foam к контракту отчетного пайплайна."""
    normalized = {
        str(key): np.asarray(value, dtype=float).reshape(-1)
        for key, value in columns.items()
    }
    _apply_column_aliases(normalized)
    _validate_required_columns(normalized)

    time_s = normalized["time_s"]
    n_rows = time_s.size
    for key, value in normalized.items():
        if value.size != n_rows:
            raise ValueError(
                f"В колонке {key!r} {value.size} строк, ожидалось {n_rows}."
            )
    if not np.all(np.diff(time_s) > 0.0):
        raise ValueError("Временной ряд GeN-Foam должен строго возрастать.")

    fuel_center_k = normalized["fuel_center_k"]
    fuel_surface_k = normalized.get("fuel_surface_k", fuel_center_k)
    fuel_average_k = normalized.get(
        "fuel_average_k",
        0.5 * (fuel_center_k + fuel_surface_k),
    )
    clad_outer_k = normalized["clad_outer_k"]
    clad_inner_k = normalized.get("clad_inner_k", clad_outer_k)

    use_series_reference = source == "genfoam"
    if "water_energy_j_per_m" in normalized:
        water_energy_j_per_m = np.maximum(normalized["water_energy_j_per_m"], 0.0)
    elif "clad_to_water_heat_flux_w_m2" in normalized:
        water_energy_j_per_m = integrate_wall_heat_flux_j_per_m(
            time_s,
            normalized["clad_to_water_heat_flux_w_m2"],
            scenario,
        )
    elif "water_temperature_k" in normalized:
        water_energy_j_per_m = water_energy_from_temperature_j_per_m(
            normalized["water_temperature_k"],
            scenario,
        )
        if use_series_reference:
            water_energy_j_per_m = np.maximum(
                water_energy_j_per_m - water_energy_j_per_m[0],
                0.0,
            )
    else:
        raise ValueError(
            "Ряд GeN-Foam должен содержать water_temperature_k, "
            "water_energy_j_per_m или clad_to_water_heat_flux_w_m2."
        )

    fuel_reference_k = (
        float(fuel_average_k[0]) if use_series_reference else scenario.initial_solid_temperature_k
    )
    clad_reference_k = (
        float(0.5 * (clad_inner_k[0] + clad_outer_k[0]))
        if use_series_reference
        else scenario.initial_solid_temperature_k
    )
    pulse_energy_j_per_m = normalized.get(
        "pulse_energy_j_per_m",
        pulse_energy_series_j_per_m(time_s, scenario),
    )
    fuel_energy_j_per_m = normalized.get(
        "fuel_energy_j_per_m",
        _solid_energy_from_average_temperature(
            fuel_average_k,
            fuel_reference_k,
            _fuel_volume_m3_per_m(scenario),
            scenario.fuel.volumetric_heat_capacity_j_m3_k,
        ),
    )
    clad_energy_j_per_m = normalized.get(
        "clad_energy_j_per_m",
        _solid_energy_from_average_temperature(
            0.5 * (clad_inner_k + clad_outer_k),
            clad_reference_k,
            _clad_volume_m3_per_m(scenario),
            scenario.clad.volumetric_heat_capacity_j_m3_k,
        ),
    )

    result: dict[str, Any] = {
        "time_s": time_s,
        "fuel_center_k": fuel_center_k,
        "fuel_surface_k": fuel_surface_k,
        "fuel_average_k": fuel_average_k,
        "clad_inner_k": clad_inner_k,
        "clad_outer_k": clad_outer_k,
        "fuel_energy_j_per_m": fuel_energy_j_per_m,
        "clad_energy_j_per_m": clad_energy_j_per_m,
        "water_energy_j_per_m": water_energy_j_per_m,
        "pulse_energy_j_per_m": pulse_energy_j_per_m,
        "energy_residual_j_per_m": (
            pulse_energy_j_per_m
            - fuel_energy_j_per_m
            - clad_energy_j_per_m
            - water_energy_j_per_m
        ),
        "scenario": scenario,
        "thermal_source": source,
        "thermal_provenance": str(provenance) if provenance is not None else "",
    }
    if "pressure_pa" in normalized:
        result["pressure_pa"] = normalized["pressure_pa"]
    if "genfoam_total_power_w" in normalized:
        result["genfoam_total_power_w"] = normalized["genfoam_total_power_w"]
    result.update(vectorized_water_state(water_energy_j_per_m, scenario.water))

    if "water_temperature_k" in normalized:
        result["water_temperature_k"] = normalized["water_temperature_k"]
    result.update(_minimal_radial_profile(result, scenario))
    return result


def _apply_column_aliases(columns: dict[str, np.ndarray]) -> None:
    aliases = {
        "time": "time_s",
        "t_s": "time_s",
        "steam_temperature_k": "water_temperature_k",
        "gas_temperature_k": "water_temperature_k",
        "steam_energy_j_per_m": "water_energy_j_per_m",
        "heat_to_water_j_per_m": "water_energy_j_per_m",
        "wall_heat_flux_w_m2": "clad_to_water_heat_flux_w_m2",
        "q_wall_w_m2": "clad_to_water_heat_flux_w_m2",
    }
    for source, target in aliases.items():
        if source in columns and target not in columns:
            columns[target] = columns[source]


def _validate_required_columns(columns: Mapping[str, np.ndarray]) -> None:
    missing = [
        key for key in ("time_s", "fuel_center_k", "clad_outer_k") if key not in columns
    ]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"В выгрузке GeN-Foam нет колонок: {missing_text}.")


def _fuel_volume_m3_per_m(scenario: Scenario) -> float:
    geometry = scenario.geometry
    return float(
        np.pi * (geometry.fuel_radius_m**2 - geometry.fuel_inner_radius_m**2)
    )


def _clad_volume_m3_per_m(scenario: Scenario) -> float:
    geometry = scenario.geometry
    return float(
        np.pi * (geometry.clad_outer_radius_m**2 - geometry.gap_outer_radius_m**2)
    )


def _solid_energy_from_average_temperature(
    average_temperature_k: np.ndarray,
    initial_temperature_k: float,
    volume_m3_per_m: float,
    volumetric_heat_capacity_j_m3_k: float,
) -> np.ndarray:
    return np.maximum(
        (average_temperature_k - initial_temperature_k)
        * volume_m3_per_m
        * volumetric_heat_capacity_j_m3_k,
        0.0,
    )


def _minimal_radial_profile(
    result: Mapping[str, Any],
    scenario: Scenario,
) -> dict[str, np.ndarray]:
    geometry = scenario.geometry
    r_m = np.array(
        [
            geometry.fuel_inner_radius_m,
            geometry.fuel_radius_m,
            geometry.gap_outer_radius_m,
            geometry.clad_outer_radius_m,
        ],
        dtype=float,
    )
    temperature_profile_k = np.column_stack(
        [
            result["fuel_center_k"],
            result["fuel_surface_k"],
            result["clad_inner_k"],
            result["clad_outer_k"],
        ]
    )
    return {
        "r_m": r_m,
        "tag": np.array([0, 0, 1, 1], dtype=np.int8),
        "temperature_profile_k": temperature_profile_k,
    }
