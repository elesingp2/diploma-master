from __future__ import annotations

from typing import Any

import numpy as np


def _first_time_or_nan(time_s: np.ndarray, mask: np.ndarray) -> float:
    if not np.any(mask):
        return float("nan")
    return float(time_s[np.argmax(mask)])


def _percent(part: float, whole: float) -> float:
    if whole <= 0.0:
        return float("nan")
    return 100.0 * part / whole


def _energy_funnel_index(result: dict[str, Any], checkpoint: str) -> int:
    if checkpoint == "final":
        return -1
    if checkpoint != "before_limits":
        raise ValueError("checkpoint must be 'final' or 'before_limits'.")

    scenario = result["scenario"]
    fuel_center_k = np.asarray(result["fuel_center_k"])
    clad_outer_k = np.asarray(result["clad_outer_k"])
    material_ok = (
        fuel_center_k < scenario.fuel.melting_temperature_k
    ) & (clad_outer_k < scenario.clad.limit_temperature_k)
    if not np.any(material_ok):
        return 0
    return int(np.flatnonzero(material_ok)[-1])


def build_energy_funnel(
    result: dict[str, Any],
    checkpoint: str = "final",
) -> dict[str, Any]:
    """Строит диагностическую воронку энергии по ряду GeN-Foam."""
    idx = _energy_funnel_index(result, checkpoint)
    time_s = float(np.asarray(result["time_s"])[idx])
    pulse_j_per_m = float(np.asarray(result["pulse_energy_j_per_m"])[idx])
    fuel_j_per_m = float(np.asarray(result["fuel_energy_j_per_m"])[idx])
    clad_j_per_m = float(np.asarray(result["clad_energy_j_per_m"])[idx])
    steam_j_per_m = float(np.asarray(result["water_energy_j_per_m"])[idx])
    residual_j_per_m = float(np.asarray(result["energy_residual_j_per_m"])[idx])

    after_gap_j_per_m = clad_j_per_m + steam_j_per_m
    stages = [
        {
            "stage": "топливо и газовый зазор",
            "meaning": "энергия, не дошедшая до оболочки за время расчета",
            "stage_input_kj_per_m": pulse_j_per_m / 1e3,
            "retained_or_blocked_kj_per_m": fuel_j_per_m / 1e3,
            "retained_or_blocked_percent_of_pulse": _percent(
                fuel_j_per_m,
                pulse_j_per_m,
            ),
            "retained_or_blocked_percent_of_stage_input": _percent(
                fuel_j_per_m,
                pulse_j_per_m,
            ),
            "passed_forward_kj_per_m": after_gap_j_per_m / 1e3,
            "passed_forward_percent_of_pulse": _percent(
                after_gap_j_per_m,
                pulse_j_per_m,
            ),
            "passed_forward_percent_of_stage_input": _percent(
                after_gap_j_per_m,
                pulse_j_per_m,
            ),
        },
        {
            "stage": "оболочка",
            "meaning": "энергия, накопленная в металле оболочки",
            "stage_input_kj_per_m": after_gap_j_per_m / 1e3,
            "retained_or_blocked_kj_per_m": clad_j_per_m / 1e3,
            "retained_or_blocked_percent_of_pulse": _percent(
                clad_j_per_m,
                pulse_j_per_m,
            ),
            "retained_or_blocked_percent_of_stage_input": _percent(
                clad_j_per_m,
                after_gap_j_per_m,
            ),
            "passed_forward_kj_per_m": steam_j_per_m / 1e3,
            "passed_forward_percent_of_pulse": _percent(
                steam_j_per_m,
                pulse_j_per_m,
            ),
            "passed_forward_percent_of_stage_input": _percent(
                steam_j_per_m,
                after_gap_j_per_m,
            ),
        },
    ]

    return {
        "checkpoint": checkpoint,
        "time_s": time_s,
        "pulse_energy_kj_per_m": pulse_j_per_m / 1e3,
        "steam_energy_kj_per_m": steam_j_per_m / 1e3,
        "steam_energy_percent_of_pulse": _percent(steam_j_per_m, pulse_j_per_m),
        "numerical_residual_kj_per_m": residual_j_per_m / 1e3,
        "numerical_residual_percent_of_pulse": _percent(
            residual_j_per_m,
            pulse_j_per_m,
        ),
        "stages": stages,
    }


def build_scenario_report(
    label: str,
    result: dict[str, Any],
    validation: dict[str, Any],
    chemistry: dict[str, Any] | None = None,
) -> dict[str, float | str | bool]:
    scenario = result["scenario"]
    metrics = validation["metrics"]
    checks = validation["checks"]
    threshold_reached = bool(metrics["chemistry_threshold_reached"])
    below_melting = bool(checks["fuel_below_melting"] and checks["clad_below_melting"])
    below_temperature_limits = bool(
        checks["fuel_below_melting"] and checks["clad_below_temperature_limit"]
    )
    threshold_before_limits = bool(metrics["threshold_reached_before_material_limits"])

    time_s = np.asarray(result["time_s"])
    gas_temperature_k = np.asarray(result["water_temperature_k"])
    fuel_center_k = np.asarray(result["fuel_center_k"])
    clad_outer_k = np.asarray(result["clad_outer_k"])
    material_ok = (
        fuel_center_k < scenario.fuel.melting_temperature_k
    ) & (clad_outer_k < scenario.clad.limit_temperature_k)
    threshold_mask = gas_temperature_k >= scenario.chemistry_threshold_k
    gas_peak_index = int(np.argmax(gas_temperature_k))
    if np.any(material_ok):
        max_gas_before_limits_k = float(np.max(gas_temperature_k[material_ok]))
    else:
        max_gas_before_limits_k = float("nan")

    final_pulse_energy = float(result["pulse_energy_j_per_m"][-1])
    final_water_energy = float(result["water_energy_j_per_m"][-1])
    energy_to_water_percent = (
        100.0 * final_water_energy / final_pulse_energy
        if final_pulse_energy > 0.0
        else float("nan")
    )

    max_fuel_k = float(metrics["max_fuel_center_k"])
    max_clad_k = float(metrics["max_clad_outer_k"])
    max_gas_k = float(metrics["max_gas_or_water_temperature_k"])

    if threshold_before_limits and below_temperature_limits:
        interpretation = "целевое температурное окно достигнуто без нарушения пределов топлива и оболочки"
    elif threshold_reached and not below_temperature_limits:
        interpretation = "целевое температурное окно достигается вместе с нарушением пределов топлива или оболочки"
    elif below_temperature_limits:
        interpretation = "пределы топлива и оболочки не нарушены, но целевое температурное окно не достигнуто"
    else:
        interpretation = "предел топлива или оболочки нарушается раньше целевого режима"

    layer_thickness_um = np.nan
    if scenario.steam_layer is not None:
        layer_thickness_um = scenario.steam_layer.thickness_m * 1e6
    if scenario.annular_water_layer is not None:
        layer_thickness_um = scenario.annular_water_layer.thickness_m * 1e6

    return {
        "case": label,
        "fuel": scenario.fuel.name,
        "clad": scenario.clad.name,
        "pulse_kj_per_m": scenario.pulse.energy_j_per_m / 1e3,
        "layer_thickness_um": layer_thickness_um,
        "max_gas_k": max_gas_k,
        "max_gas_before_limits_k": max_gas_before_limits_k,
        "max_gas_time_s": float(time_s[gas_peak_index]),
        "chemistry_threshold_k": float(metrics["chemistry_threshold_k"]),
        "target_margin_k": max_gas_k - float(metrics["chemistry_threshold_k"]),
        "target_margin_before_limits_k": max_gas_before_limits_k
        - float(metrics["chemistry_threshold_k"]),
        "max_fuel_k": max_fuel_k,
        "fuel_melting_k": float(metrics["fuel_melting_temperature_k"]),
        "fuel_margin_k": scenario.fuel.melting_temperature_k - max_fuel_k,
        "max_clad_k": max_clad_k,
        "clad_melting_k": float(metrics["clad_melting_temperature_k"]),
        "clad_limit_k": float(metrics["clad_temperature_limit_k"]),
        "clad_margin_k": scenario.clad.melting_temperature_k - max_clad_k,
        "clad_limit_margin_k": scenario.clad.limit_temperature_k - max_clad_k,
        "threshold_reached": threshold_reached,
        "threshold_time_s": _first_time_or_nan(time_s, threshold_mask),
        "threshold_before_material_limits": threshold_before_limits,
        "threshold_before_limits_time_s": _first_time_or_nan(
            time_s,
            threshold_mask & material_ok,
        ),
        "below_melting": below_melting,
        "below_temperature_limits": below_temperature_limits,
        "energy_to_water_percent": energy_to_water_percent,
        "final_water_energy_kj_per_m": final_water_energy / 1e3,
        "final_vapor_quality": float(result["vapor_quality"][-1]),
        "peak_h2_g_per_m": (
            float(chemistry["peak_hydrogen_g_per_m"]) if chemistry else 0.0
        ),
        "interpretation": interpretation,
    }


def build_pipeline_takeaways(
    reports: list[dict[str, float | str | bool]],
) -> dict[str, Any]:
    """Собирает компактный вывод для ноутбука."""
    main_reading = []
    for report in reports:
        main_reading.append(
            (
                f"{report['case']}: {report['interpretation']}; "
                f"T_s^max до пределов={report['max_gas_before_limits_k']:.0f} K; "
                f"M_об={report['clad_limit_margin_k']:.0f} K; "
                f"равновесный H2={report['peak_h2_g_per_m']:.3g} г/м."
            )
        )

    return {
        "reports": reports,
        "main_reading": main_reading,
        "missing_work": [
            "подготовить воспроизводимые GeN-Foam кейсы и экспорт тепловых рядов для всех сценариев",
            "зафиксировать Cantera-механизм и проверить равновесный состав высокотемпературного пара",
            "заменить постоянные свойства воды и пара на IAPWS или проверенные таблицы",
            "добавить режимы теплообмена: конвекцию, кризис теплообмена и пленочное кипение",
            "отделить целевой термолиз от аварийной пароциркониевой реакции",
            "оформить материалы-кандидаты отдельной версией пайплайна с проверкой нейтроники, окисления, теплового удара и радиационных ограничений",
            "сравнить результат на границе промышленной площадки с внешним электролизом, высокотемпературным паровым электролизом и высокотемпературными газоохлаждаемыми реакторами",
        ],
    }
