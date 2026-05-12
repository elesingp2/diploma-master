from __future__ import annotations

from typing import Any, TypedDict

import numpy as np

from .scenarios import Scenario


class ValidationReport(TypedDict):
    ok: bool
    checks: dict[str, bool]
    metrics: dict[str, float | bool]


def validate_physical_consistency(
    result: dict[str, Any],
) -> ValidationReport:
    scenario = result["scenario"]
    if not isinstance(scenario, Scenario):
        raise TypeError("В результате должен быть Scenario в поле 'scenario'.")

    time_s = np.asarray(result["time_s"])
    residual = np.asarray(result["energy_residual_j_per_m"])
    pulse_energy = max(float(scenario.pulse.energy_j_per_m), 1.0)
    fuel_center_k = np.asarray(result["fuel_center_k"])
    clad_outer_k = np.asarray(result["clad_outer_k"])
    clad_limit_k = scenario.clad.limit_temperature_k
    gas_temperature_k = np.asarray(result["water_temperature_k"])
    temperature_profile_k = np.asarray(result["temperature_profile_k"])
    vapor_quality = np.asarray(result["vapor_quality"])
    water_energy_j_per_m = np.asarray(result["water_energy_j_per_m"])

    max_residual_rel = float(np.max(np.abs(residual)) / pulse_energy)
    energy_balance_ok = (
        bool(np.all(np.isfinite(residual)))
        if result.get("thermal_source") == "genfoam"
        else max_residual_rel < 1e-8
    )
    chemistry_mask = gas_temperature_k >= scenario.chemistry_threshold_k
    material_ok_mask = (
        fuel_center_k < scenario.fuel.melting_temperature_k
    ) & (clad_outer_k < clad_limit_k)
    checks = {
        "time_monotonic": bool(np.all(np.diff(time_s) > 0.0)),
        "finite_temperatures": bool(
            np.all(np.isfinite(temperature_profile_k))
            and np.all(temperature_profile_k > 0.0)
        ),
        "energy_balance_ok": energy_balance_ok,
        "water_energy_nonnegative": bool(np.all(water_energy_j_per_m >= 0.0)),
        "vapor_quality_in_range": bool(
            np.all(vapor_quality >= 0.0) and np.all(vapor_quality <= 1.0)
        ),
        "fuel_below_melting": bool(
            np.max(fuel_center_k) < scenario.fuel.melting_temperature_k
        ),
        "clad_below_melting": bool(
            np.max(clad_outer_k) < scenario.clad.melting_temperature_k
        ),
        "clad_below_temperature_limit": bool(np.max(clad_outer_k) < clad_limit_k),
    }
    metrics = {
        "max_energy_residual_relative": max_residual_rel,
        "max_fuel_center_k": float(np.max(fuel_center_k)),
        "max_clad_outer_k": float(np.max(clad_outer_k)),
        "max_gas_or_water_temperature_k": float(np.max(gas_temperature_k)),
        "final_vapor_quality": float(vapor_quality[-1]),
        "final_water_energy_kj_per_m": float(water_energy_j_per_m[-1] / 1e3),
        "chemistry_threshold_k": float(scenario.chemistry_threshold_k),
        "fuel_melting_temperature_k": float(scenario.fuel.melting_temperature_k),
        "clad_melting_temperature_k": float(scenario.clad.melting_temperature_k),
        "clad_temperature_limit_k": float(clad_limit_k),
        "chemistry_threshold_reached": bool(np.any(chemistry_mask)),
        "threshold_reached_before_material_limits": bool(
            np.any(chemistry_mask & material_ok_mask)
        ),
    }
    numerical_checks = (
        "time_monotonic",
        "finite_temperatures",
        "energy_balance_ok",
        "water_energy_nonnegative",
        "vapor_quality_in_range",
    )
    return {
        "ok": all(checks[name] for name in numerical_checks),
        "checks": checks,
        "metrics": metrics,
    }
