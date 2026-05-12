from __future__ import annotations

from typing import Any

import numpy as np

from .genfoam_post import canonicalize_thermal_series, pulse_energy_series_j_per_m
from .scenarios import Scenario
from .water_state import water_state_from_energy


def simulate_python_fallback(scenario: Scenario) -> dict[str, Any]:
    """Считает трехузловой тепловой fallback, если GeN-Foam недоступен."""
    time_s = _time_grid(scenario.t_end_s)
    fuel_capacity = _fuel_capacity_j_k_m(scenario)
    clad_capacity = _clad_capacity_j_k_m(scenario)
    fuel_to_clad_w_k_m = _fuel_to_clad_conductance_w_k_m(scenario)
    clad_to_steam_w_k_m = (
        scenario.water.heat_transfer_coefficient_w_m2_k
        * _outer_area_m2_per_m(scenario)
    )

    fuel_energy = np.zeros_like(time_s)
    clad_energy = np.zeros_like(time_s)
    steam_energy = np.zeros_like(time_s)
    wall_flux = np.zeros_like(time_s)
    pulse_energy = pulse_energy_series_j_per_m(time_s, scenario)

    for i in range(1, time_s.size):
        dt = time_s[i] - time_s[i - 1]
        deposited = pulse_energy[i] - pulse_energy[i - 1]
        fuel_t = scenario.initial_solid_temperature_k + fuel_energy[i - 1] / fuel_capacity
        clad_t = scenario.initial_solid_temperature_k + clad_energy[i - 1] / clad_capacity
        steam_t = water_state_from_energy(steam_energy[i - 1], scenario.water).temperature_k

        heat_fc = fuel_to_clad_w_k_m * (fuel_t - clad_t) * dt
        heat_fc = _bounded_exchange(heat_fc, fuel_energy[i - 1] + deposited, clad_energy[i - 1])
        heat_cs = max(clad_to_steam_w_k_m * (clad_t - steam_t) * dt, 0.0)
        heat_cs = _bounded_exchange(heat_cs, clad_energy[i - 1] + heat_fc, steam_energy[i - 1])

        fuel_energy[i] = fuel_energy[i - 1] + deposited - heat_fc
        clad_energy[i] = clad_energy[i - 1] + heat_fc - heat_cs
        steam_energy[i] = steam_energy[i - 1] + heat_cs
        wall_flux[i] = heat_cs / max(dt * _outer_area_m2_per_m(scenario), 1e-30)

    temperatures = _solid_temperatures(
        scenario,
        fuel_energy,
        clad_energy,
        steam_energy,
        fuel_capacity,
        clad_capacity,
    )
    columns = {
        "time_s": time_s,
        "fuel_energy_j_per_m": fuel_energy,
        "clad_energy_j_per_m": clad_energy,
        "water_energy_j_per_m": steam_energy,
        "pulse_energy_j_per_m": pulse_energy,
        "pressure_pa": np.full_like(time_s, scenario.water.pressure_pa),
        "clad_to_water_heat_flux_w_m2": wall_flux,
        **temperatures,
    }
    return canonicalize_thermal_series(
        columns,
        scenario,
        source="python_fallback",
        provenance=(
            "three-node lumped Python fallback; external GeN-Foam thermal "
            "series is unavailable or not accepted for this scenario"
        ),
    )


def _time_grid(t_end_s: float) -> np.ndarray:
    fine_end = min(max(t_end_s, 0.0), 1.0)
    early = np.linspace(0.0, fine_end, max(int(fine_end / 0.002) + 1, 2))
    if t_end_s <= fine_end:
        return early
    late = np.linspace(fine_end + 0.01, t_end_s, max(int((t_end_s - fine_end) / 0.01), 2))
    return np.concatenate([early, late])


def _fuel_capacity_j_k_m(scenario: Scenario) -> float:
    return (
        np.pi
        * scenario.geometry.fuel_radius_m**2
        * scenario.fuel.volumetric_heat_capacity_j_m3_k
    )


def _clad_capacity_j_k_m(scenario: Scenario) -> float:
    geometry = scenario.geometry
    return (
        np.pi
        * (geometry.clad_outer_radius_m**2 - geometry.gap_outer_radius_m**2)
        * scenario.clad.volumetric_heat_capacity_j_m3_k
    )


def _outer_area_m2_per_m(scenario: Scenario) -> float:
    return 2.0 * np.pi * scenario.geometry.clad_outer_radius_m


def _fuel_to_clad_conductance_w_k_m(scenario: Scenario) -> float:
    geometry = scenario.geometry
    gap_area = 2.0 * np.pi * geometry.fuel_radius_m
    gap_g = scenario.gap_conductance_w_m2_k * gap_area
    clad_g = 2.0 * np.pi * scenario.clad.conductivity_w_m_k / np.log(
        geometry.clad_outer_radius_m / geometry.gap_outer_radius_m
    )
    fuel_g = 8.0 * np.pi * max(scenario.fuel.conductivity_w_m_k, 1e-9)
    return 1.0 / (1.0 / fuel_g + 1.0 / gap_g + 1.0 / clad_g)


def _bounded_exchange(heat_j_per_m: float, donor_energy: float, receiver_energy: float) -> float:
    if heat_j_per_m >= 0.0:
        return min(heat_j_per_m, max(donor_energy, 0.0))
    return -min(-heat_j_per_m, max(receiver_energy, 0.0))


def _solid_temperatures(
    scenario: Scenario,
    fuel_energy: np.ndarray,
    clad_energy: np.ndarray,
    steam_energy: np.ndarray,
    fuel_capacity: float,
    clad_capacity: float,
) -> dict[str, np.ndarray]:
    fuel_average = scenario.initial_solid_temperature_k + fuel_energy / fuel_capacity
    clad_average = scenario.initial_solid_temperature_k + clad_energy / clad_capacity
    steam_temperature = np.array(
        [water_state_from_energy(energy, scenario.water).temperature_k for energy in steam_energy],
        dtype=float,
    )
    fuel_gradient = np.clip(0.28 * np.maximum(fuel_average - clad_average, 0.0), 0.0, 900.0)
    clad_gradient = np.clip(0.10 * np.maximum(clad_average - steam_temperature, 0.0), 0.0, 450.0)
    return {
        "fuel_average_k": fuel_average,
        "fuel_center_k": fuel_average + fuel_gradient,
        "fuel_surface_k": fuel_average - fuel_gradient,
        "clad_inner_k": clad_average + clad_gradient,
        "clad_outer_k": clad_average - clad_gradient,
        "water_temperature_k": steam_temperature,
    }
