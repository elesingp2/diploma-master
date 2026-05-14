from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from .cantera_equilibrium import (
    compute_equilibrium_hydrogen,
    compute_python_hydrogen_proxy,
)
from .fallback_physics import simulate_python_fallback
from .genfoam_io import load_genfoam_case
from .plots import (
    plot_chemistry_temperature_margin,
    plot_energy_balance,
    plot_pin_cross_section,
    plot_radial_temperature_map,
    plot_radial_temperature_profiles,
    plot_temperature_history,
    plot_water_state,
)
from .reports import build_energy_funnel, build_scenario_report
from .scenarios import (
    AnnularWaterLayer,
    Material,
    PinGeometry,
    Pulse,
    build_annular_water_scenario,
    scenario_summary,
)
from .validation import validate_physical_consistency
from .wall_coupled_water import apply_wall_coupled_water_model


PIPELINE_VERSION = "zircaloy-v1"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def repo_relative_path(env_name: str, default: str) -> Path:
    """Возвращает абсолютный путь, считая относительные значения от корня проекта."""
    raw_path = Path(os.environ.get(env_name, default))
    return raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path


DEFAULT_GENFOAM_CASE_PATH = repo_relative_path(
    "GENFOAM_V1_CASE_PATH",
    "data/genfoam/near_wall_steam_layer",
)


@dataclass(frozen=True)
class ScenarioRun:
    label: str
    scenario: Any
    result: dict[str, Any]
    chemistry: dict[str, Any]
    validation: dict[str, Any]
    report: dict[str, float | str | bool]


def build_notebook_baseline_scenario():
    """Возвращает базовый сценарий для первого ноутбука и LaTeX-экспорта."""
    geometry = PinGeometry(
        fuel_radius_m=4.00e-3,
        gap_outer_radius_m=4.08e-3,
        clad_outer_radius_m=4.68e-3,
        length_m=1.0,
        n_fuel=32,
        n_clad=10,
    )
    fuel = Material(
        name="UO2",
        conductivity_w_m_k=3.5,
        volumetric_heat_capacity_j_m3_k=3.0e6,
        melting_temperature_k=3120.0,
    )
    clad = Material(
        name="Zircaloy",
        conductivity_w_m_k=18.0,
        volumetric_heat_capacity_j_m3_k=2.0e6,
        melting_temperature_k=2125.0,
        allowable_temperature_k=1477.0,
    )
    pulse = Pulse(
        energy_j_per_m=2.5e5,
        duration_s=0.20,
        shape="square",
    )
    water_layer = AnnularWaterLayer(
        thickness_m=1.0e-4,
        pressure_pa=15.5e6,
        initial_temperature_k=620.0,
        saturation_temperature_k=620.0,
        liquid_density_kg_m3=650.0,
        cp_liquid_j_kg_k=6.0e3,
        latent_heat_j_kg=1.10e6,
        cp_vapor_j_kg_k=2.6e3,
        wall_temperature_cap=True,
    )
    return build_annular_water_scenario(
        geometry=geometry,
        fuel=fuel,
        clad=clad,
        pulse=pulse,
        annular_water_layer=water_layer,
        gap_conductance_w_m2_k=5.0e3,
        t_end_s=20.0,
        chemistry_threshold_k=3273.15,
        genfoam_case_path=str(DEFAULT_GENFOAM_CASE_PATH),
    )


def run_scenario(
    label: str,
    scenario,
    *,
    genfoam_case_path: str | Path | None = None,
    allow_python_fallback: bool = False,
) -> ScenarioRun:
    case_path = genfoam_case_path or scenario.genfoam_case_path
    if case_path is None:
        raise ValueError(
            "В сценарии нужен genfoam_case_path или явный аргумент "
            "genfoam_case_path для run_scenario."
        )
    try:
        result = load_genfoam_case(case_path, scenario)
        result = apply_wall_coupled_water_model(result, scenario)
        chemistry = compute_equilibrium_hydrogen(result, scenario)
    except (FileNotFoundError, NotADirectoryError) as exc:
        if not allow_python_fallback:
            raise
        result = simulate_python_fallback(scenario)
        result["fallback_reason"] = str(exc)
        chemistry = compute_python_hydrogen_proxy(result, scenario)
    validation = validate_physical_consistency(result)
    report = build_scenario_report(label, result, validation, chemistry)
    return ScenarioRun(
        label=label,
        scenario=scenario,
        result=result,
        chemistry=chemistry,
        validation=validation,
        report=report,
    )


def run_notebook_pipeline(
    *,
    genfoam_case_path: str | Path | None = None,
    allow_python_fallback: bool = False,
) -> dict[str, ScenarioRun]:
    baseline = build_notebook_baseline_scenario()
    return {
        "baseline": run_scenario(
            r"\(\mathrm{UO_2}\)--Zircaloy, версия 1",
            baseline,
            genfoam_case_path=genfoam_case_path,
            allow_python_fallback=allow_python_fallback,
        ),
    }


def make_pipeline_geometry(run: ScenarioRun):
    fig, ax = plt.subplots(figsize=(6.8, 5.8), constrained_layout=True)
    plot_pin_cross_section(run.scenario, ax)
    return fig


def make_pipeline_temperature_history(run: ScenarioRun):
    fig, ax = plt.subplots(figsize=(7.8, 4.2), constrained_layout=True)
    plot_temperature_history(run.result, ax)
    return fig


def make_pipeline_radial_temperature_map(run: ScenarioRun):
    fig, ax = plt.subplots(figsize=(8.6, 5.1), constrained_layout=True)
    plot_radial_temperature_map(run.result, ax)
    return fig


def make_pipeline_radial_temperature_profiles(run: ScenarioRun):
    fig, ax = plt.subplots(figsize=(8.6, 4.9), constrained_layout=True)
    plot_radial_temperature_profiles(run.result, ax=ax)
    return fig


def make_pipeline_energy_balance(run: ScenarioRun):
    fig, ax = plt.subplots(figsize=(7.8, 4.2), constrained_layout=True)
    plot_energy_balance(run.result, ax)
    return fig


def make_pipeline_steam_state(run: ScenarioRun):
    fig, ax = plt.subplots(figsize=(8.6, 4.9), constrained_layout=True)
    plot_water_state(run.result, run.chemistry, ax)
    return fig


def make_pipeline_chemistry_window(run: ScenarioRun):
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    plot_chemistry_temperature_margin(run.result, ax)
    return fig


def _format_bool(value: bool) -> str:
    return "да" if value else "нет"


def _format_float(value: float, digits: int = 2) -> str:
    if abs(value) < 1e-3 and value != 0.0:
        mantissa, exponent = f"{value:.2e}".split("e")
        return rf"\ensuremath{{{float(mantissa):.{digits}f}\cdot10^{{{int(exponent)}}}}}"
    return f"{value:.{digits}f}"


def _format_percent(value: float) -> str:
    return _format_float(value, 3 if abs(value) < 1.0 else 2)


def _capitalize_first(value: str) -> str:
    return value[:1].upper() + value[1:]


def _thermal_source_phrases(result: dict[str, Any]) -> tuple[str, str]:
    source = result.get("thermal_source", "")
    if source == "genfoam":
        return "тепловой ряд GeN-Foam", "по выгруженному ряду GeN-Foam"
    if source == "python_fallback":
        return "явный трехузловой Python fallback", "по расчетному ряду fallback"
    return "внешний тепловой ряд", "по входному тепловому ряду"


def _chemistry_model_text(run: ScenarioRun) -> str:
    if bool(run.chemistry.get("uses_cantera")):
        return r"""Равновесная химия считается в Cantera по состоянию пара из теплового ряда:
\[
T_s(t),\quad p_s(t),\quad X_0=\{H_2O:1\},
\qquad
m_{H_2}^{eq}=n_{H_2}^{eq}M_{H_2}.
\]"""
    return r"""Химический блок в этом прогоне не является расчетом Cantera: для явно включенного fallback используется пороговая верхняя оценка \(H_2\), ограниченная стехиометрическим запасом воды:
\[
T_s(t),\quad p_s(t),\quad m_s'(t)
\;\longrightarrow\;
m_{H_2}^{proxy}\le m_s'\frac{M_{H_2}}{M_{H_2O}}.
\]"""


def _write_pipeline_tex(path: Path, runs: dict[str, ScenarioRun]) -> None:
    baseline = runs["baseline"]
    summary = scenario_summary(baseline.scenario)
    baseline_report = baseline.report
    geometry = baseline.scenario.geometry
    fuel_heat_capacity_j_k_m = (
        math.pi
        * geometry.fuel_radius_m**2
        * baseline.scenario.fuel.volumetric_heat_capacity_j_m3_k
    )
    clad_heat_capacity_j_k_m = (
        math.pi
        * (geometry.clad_outer_radius_m**2 - geometry.gap_outer_radius_m**2)
        * baseline.scenario.clad.volumetric_heat_capacity_j_m3_k
    )
    steam_heat_capacity_j_k_m = (
        baseline.scenario.water.mass_kg_per_m
        * baseline.scenario.water.cp_vapor_j_kg_k
    )
    steam_heat_capacity_share_percent = (
        100.0
        * steam_heat_capacity_j_k_m
        / (
            fuel_heat_capacity_j_k_m
            + clad_heat_capacity_j_k_m
            + steam_heat_capacity_j_k_m
        )
    )
    result_row = " & ".join(
        [
            str(baseline_report["case"]),
            _format_float(float(baseline_report["pulse_kj_per_m"]), 0),
            _format_float(float(baseline_report["max_gas_before_limits_k"]), 0),
            _format_float(float(baseline_report["clad_limit_margin_k"]), 0),
            rf"\({_format_float(float(baseline_report['peak_h2_g_per_m']), 2)}\)",
            str(baseline_report["interpretation"]),
        ]
    )
    energy_funnel = build_energy_funnel(baseline.result)
    energy_funnel_before_limits = build_energy_funnel(
        baseline.result,
        checkpoint="before_limits",
    )
    funnel_rows = "\n".join(
        "    "
        + " & ".join(
            [
                _capitalize_first(str(stage["stage"])),
                _format_float(float(stage["retained_or_blocked_kj_per_m"]), 2),
                _format_percent(
                    float(stage["retained_or_blocked_percent_of_pulse"]),
                ),
                _format_percent(
                    float(stage["retained_or_blocked_percent_of_stage_input"]),
                ),
                _format_float(float(stage["passed_forward_kj_per_m"]), 2),
                _format_percent(float(stage["passed_forward_percent_of_pulse"])),
            ]
        )
        + r" \\"
        for stage in energy_funnel["stages"]
    )

    fuel_margin_k = float(baseline_report["fuel_margin_k"])
    clad_limit_margin_k = float(baseline_report["clad_limit_margin_k"])
    target_margin_before_limits_k = float(
        baseline_report["target_margin_before_limits_k"]
    )
    max_gas_before_limits_k = float(baseline_report["max_gas_before_limits_k"])
    thermal_source_text, thermal_series_text = _thermal_source_phrases(baseline.result)
    chemistry_model_text = _chemistry_model_text(baseline)
    h2_metric_label = (
        r"m_{H_2}^{eq}"
        if bool(baseline.chemistry.get("uses_cantera"))
        else r"m_{H_2}^{proxy}"
    )
    threshold_phrase = (
        rf"Водно-паровой слой достигает порога \(T^*_{{\mathrm{{дис}}}}={summary['chemistry_threshold_k']:.0f}\,\mathrm{{K}}\)"
        if bool(baseline_report["threshold_reached"])
        else rf"Водно-паровой слой не достигает порога \(T^*_{{\mathrm{{дис}}}}={summary['chemistry_threshold_k']:.0f}\,\mathrm{{K}}\)"
    )
    clad_phrase = (
        "оболочка остается ниже принятого температурного предела"
        if clad_limit_margin_k >= 0.0
        else "оболочка выходит выше принятого температурного предела"
    )
    if bool(baseline_report["threshold_before_material_limits"]):
        final_reading = (
            "Итог версии 1 является положительным только как тепловой признак: "
            "целевое температурное окно достигается до нарушения пределов топлива "
            "и оболочки. Следующий обязательный шаг -- отдельная постановка "
            "паровой химии и квалификация материала оболочки."
        )
    elif bool(baseline_report["below_temperature_limits"]):
        final_reading = (
            "Итог версии 1 является отрицательным по термохимическому критерию: "
            "в принятом тепловом ряду топливо и оболочка остаются ниже своих "
            "пределов, но водно-паровой слой не выходит к выбранному порогу "
            r"\(T^*_{\mathrm{дис}}\)."
        )
    else:
        final_reading = (
            "Итог версии 1 является отрицательным по материалам: целевое окно "
            "не подтверждается до нарушения принятого предела топлива или оболочки."
        )

    text = rf"""\subsection{{Версия 1 расчетной цепочки: \texorpdfstring{{\(\mathrm{{UO_2}}\)--Zircaloy}}{{UO2--Zircaloy}}}}

Эта версия фиксирует штатную пару \(\mathrm{{UO_2}}\)--Zircaloy и использует {thermal_source_text}; идентификатор расчета -- \texttt{{{PIPELINE_VERSION}}}. Рассматривается один метр твэла с радиусом топлива \(R_f={summary["fuel_radius_mm"]:.2f}\,\mathrm{{мм}}\), зазором \({summary["gap_thickness_um"]:.0f}\,\mu\mathrm{{m}}\), оболочкой толщиной \({summary["clad_thickness_mm"]:.2f}\,\mathrm{{мм}}\) и приповерхностным слоем воды толщиной \(\delta_w={summary["water_layer_thickness_um"]:.0f}\,\mu\mathrm{{m}}\) при \(p_w={summary["water_layer_pressure_mpa"]:.1f}\,\mathrm{{МПа}}\). Входной импульс равен \(E_{{\mathrm{{вв}}}}={summary["pulse_energy_kj_per_m"]:.0f}\,\mathrm{{кДж/м}}\), а для оболочки используется допустимый предел \(T_{{\mathrm{{lim}},c}}={float(baseline_report["clad_limit_k"]):.0f}\,\mathrm{{K}}\), а не температура плавления.

Масса воды у оболочки считается из кольцевого контрольного объема:
\[
m_w'=\rho_l \pi\left[(R_c+\delta_w)^2-R_c^2\right].
\]
Для выбранных параметров \(m_w'\approx{float(summary["water_layer_mass_g_per_m"]):.3f}\,\mathrm{{г/м}}\). Сначала этот слой испаряется, затем сухой пар может перегреваться. В расчет введено физическое ограничение \(T_s(t)\le T_c(t)\): пар, нагреваемый только через оболочку, не может быть горячее наружной стенки.

\begin{{figure}}[H]
    \centering
    \includegraphics[width=0.82\textwidth]{{figures/pipeline_temperature_history.png}}
    \caption{{Версия 1: история температур \(\mathrm{{UO_2}}\)--Zircaloy при \(E_{{\mathrm{{вв}}}}={summary["pulse_energy_kj_per_m"]:.0f}\,\mathrm{{кДж/м}}\). {threshold_phrase}, а {clad_phrase}.}}
    \label{{fig:pipelineTemperatureHistory}}
\end{{figure}}

Энергетический график нормирован на полную энергию импульса:
\[
\varepsilon_j(t)=\frac{{E_j(t)}}{{E_{{\mathrm{{вв}}}}}},
\qquad
j\in\{{f,c,s\}}.
\]
Здесь \(E_s\) означает энергию в локальном водно-паровом объеме около оболочки после нагрева, испарения и возможного перегрева. В версии 1 водно-паровая область получает \(\varepsilon_s\approx{float(baseline_report["energy_to_water_percent"]):.3f}\,\%\) импульса после ограничения температурой стенки. Теплоемкость сухого пара в этом объеме равна \(C_s'\approx{steam_heat_capacity_j_k_m:.3f}\,\mathrm{{Дж/(К\cdot м)}}\), но до перегрева надо также покрыть скрытую теплоту испарения.

\begin{{figure}}[H]
    \centering
    \includegraphics[width=0.82\textwidth]{{figures/pipeline_energy_balance.png}}
    \caption{{Малые доли энергии импульса, накопленные в топливе, оболочке и водно-паровом слое. Полная внесенная энергия не показана отдельной линией, чтобы не скрывать долю воды/пара порядка одного процента.}}
    \label{{fig:pipelineEnergyBalance}}
\end{{figure}}

Малую величину \(\varepsilon_s\) удобно разложить как энергетическую воронку. В строке «топливо и газовый зазор» показана энергия, которая к моменту \(t={float(energy_funnel["time_s"]):.1f}\,\mathrm{{s}}\) еще не дошла до оболочки {thermal_series_text}. В строке «оболочка» показана энергия, которая уже прошла через зазор, но осталась в металле оболочки и не была передана паровой прослойке.

\begin{{table}}[H]
    \centering
    \caption{{Энергетическая воронка версии 1 к концу расчета. Величины нормированы на \(E_{{\mathrm{{вв}}}}={summary["pulse_energy_kj_per_m"]:.0f}\,\mathrm{{кДж/м}}\).}}
    \label{{tab:pipelineEnergyFunnel}}
    \small
    \begin{{tabularx}}{{\textwidth}}{{@{{}}Xrrrrr@{{}}}}
    \toprule
    Звено & Накоплено или не прошло, кДж/м & от \(E_{{\mathrm{{вв}}}}\), \% & от входа звена, \% & Прошло дальше, кДж/м & от \(E_{{\mathrm{{вв}}}}\), \% \\
    \midrule
{funnel_rows}
    \bottomrule
    \end{{tabularx}}
\end{{table}}

Водно-паровой слой получает \(E_s\approx{float(energy_funnel["steam_energy_kj_per_m"]):.3f}\,\mathrm{{кДж/м}}\), или \({float(energy_funnel["steam_energy_percent_of_pulse"]):.3f}\,\%\) от импульса. Главный ограничитель здесь не полная энергия импульса, а температура наружной оболочки: при \(T_c\ll T^*_{{\mathrm{{дис}}}}\) перегретый пар также остается далеко ниже принятого порога.

{chemistry_model_text}
До выхода топлива и оболочки за принятые пределы водно-паровой слой успевает нагреться до \(T_s\approx{max_gas_before_limits_k:.0f}\,\mathrm{{K}}\). Полный расчетный максимум оболочки дает запас \(M_{{\mathrm{{об}}}}=T_{{\mathrm{{lim}},c}}-T_c^{{\max}}\approx{clad_limit_margin_k:.0f}\,\mathrm{{K}}\). Топливо в этой точке еще не является первым ограничением, поскольку \(M_f\approx{fuel_margin_k:.0f}\,\mathrm{{K}}\).

\begin{{table}}[H]
    \centering
    \caption{{Сводка версии 1: входной импульс и три основных выхода для \(\mathrm{{UO_2}}\)--Zircaloy.}}
    \label{{tab:pipelineScenarioReport}}
    \small
    \begin{{tabularx}}{{\textwidth}}{{@{{}}XrrrrX@{{}}}}
    \toprule
    Сценарий & \(E_{{\mathrm{{вв}}}}\), кДж/м & \(T_{{s,\max}}^{{M>0}}\), K & \(M_{{\mathrm{{об}}}}\), K & \({h2_metric_label}\), г/м & Вывод \\
    \midrule
    {result_row} \\
    \bottomrule
    \end{{tabularx}}
\end{{table}}

{final_reading} Для принятого порога \(T^*_{{\mathrm{{дис}}}}\) температурный запас пара до нарушения пределов равен \(\Delta T_{{\mathrm{{зап}}}}\approx{target_margin_before_limits_k:.0f}\,\mathrm{{K}}\), а запас оболочки в полном расчете равен \(M_{{\mathrm{{об}}}}\approx{clad_limit_margin_k:.0f}\,\mathrm{{K}}\).
"""
    path.write_text(text, encoding="utf-8")


def export_pipeline_artifacts(
    output_dir: str | Path = "figures",
    *,
    allow_python_fallback: bool = False,
) -> dict[str, ScenarioRun]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update({"figure.dpi": 140})
    runs = run_notebook_pipeline(allow_python_fallback=allow_python_fallback)
    baseline = runs["baseline"]

    figures = {
        "pipeline_temperature_history": make_pipeline_temperature_history(baseline),
        "pipeline_energy_balance": make_pipeline_energy_balance(baseline),
    }
    for stem, fig in figures.items():
        fig.savefig(output_path / f"{stem}.png", dpi=180, bbox_inches="tight")
        plt.close(fig)

    _write_pipeline_tex(output_path / "pipeline_report.tex", runs)
    return runs
