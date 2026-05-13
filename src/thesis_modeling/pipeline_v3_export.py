from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from .cantera_equilibrium import compute_equilibrium_hydrogen
from .genfoam_io import load_genfoam_case
from .material_screening import candidate_claddings, candidate_fuels, make_material_scenario
from .pipeline_export import (
    build_notebook_baseline_scenario,
    repo_relative_path,
    _format_float,
)
from .reports import build_scenario_report
from .scenarios import AnnularWaterLayer, Material, Scenario, build_annular_water_scenario
from .validation import validate_physical_consistency
from .wall_coupled_water import WallHeatTransfer, apply_wall_coupled_water_model


PIPELINE_V3_VERSION = "tvel-heating-v3"
BASE_HFC_ENERGY_J_PER_M = 480e3
BASE_PULSE_DURATION_S = 0.20


@dataclass(frozen=True)
class PipelineV3Spec:
    label: str
    fuel_name: str
    clad_name: str
    genfoam_case_path: str
    power_scale: float
    pulse_duration_s: float
    layer_thickness_m: float
    role: str


@dataclass(frozen=True)
class PipelineV3Run:
    spec: PipelineV3Spec
    scenario: Scenario
    result: dict[str, Any]
    chemistry: dict[str, Any]
    validation: dict[str, Any]
    report: dict[str, float | str | bool]
    diagnostics: dict[str, float | bool]


def pipeline_v3_specs() -> list[PipelineV3Spec]:
    return [
        PipelineV3Spec(
            label=r"\(HfC\)--W, \(4P_0\), \(1.0\,\mathrm{s}\)",
            fuel_name="HfC surrogate",
            clad_name="Tungsten",
            genfoam_case_path=str(
                repo_relative_path(
                    "GENFOAM_V3_HFC_W_S4_D1_PATH",
                    "data/genfoam/tvel-heating-v3/hfc_w_s4_d1",
                )
            ),
            power_scale=4.0,
            pulse_duration_s=1.0,
            layer_thickness_m=2.0e-4,
            role="мягкий длинный импульс: контроль безопасного, но холодного режима",
        ),
        PipelineV3Spec(
            label=r"\(HfC\)--W, \(12P_0\), \(1.0\,\mathrm{s}\)",
            fuel_name="HfC surrogate",
            clad_name="Tungsten",
            genfoam_case_path=str(
                repo_relative_path(
                    "GENFOAM_V3_HFC_W_S12_D1_PATH",
                    "data/genfoam/tvel-heating-v3/hfc_w_s12_d1",
                )
            ),
            power_scale=12.0,
            pulse_duration_s=1.0,
            layer_thickness_m=2.0e-4,
            role=r"проверка гипотезы о более длинном импульсе при той же суммарной энергии, что у \(60P_0\cdot0.2\,\mathrm{s}\)",
        ),
        PipelineV3Spec(
            label=r"\(HfC\)--W, \(60P_0\), \(0.2\,\mathrm{s}\)",
            fuel_name="HfC surrogate",
            clad_name="Tungsten",
            genfoam_case_path=str(
                repo_relative_path(
                    "GENFOAM_V3_HFC_W_S60_D02_PATH",
                    "data/genfoam/tvel-heating-v3/hfc_w_s60_d02",
                )
            ),
            power_scale=60.0,
            pulse_duration_s=0.2,
            layer_thickness_m=2.0e-4,
            role="короткий жесткий импульс: максимум прогрева топлива при той же геометрии ТВЭЛа",
        ),
    ]


def run_pipeline_v3() -> list[PipelineV3Run]:
    fuels = candidate_fuels()
    claddings = candidate_claddings()
    runs: list[PipelineV3Run] = []
    for spec in pipeline_v3_specs():
        scenario = _make_v3_scenario(
            spec,
            _material_by_name(fuels, spec.fuel_name),
            _material_by_name(claddings, spec.clad_name),
        )
        result = load_genfoam_case(spec.genfoam_case_path, scenario)
        result = apply_wall_coupled_water_model(
            result,
            scenario,
            WallHeatTransfer(max_substep_s=5.0e-4),
        )
        chemistry = compute_equilibrium_hydrogen(result, scenario)
        validation = validate_physical_consistency(result)
        report = build_scenario_report(spec.label, result, validation, chemistry)
        diagnostics = _tvel_heating_diagnostics(result, scenario, chemistry)
        runs.append(
            PipelineV3Run(
                spec=spec,
                scenario=scenario,
                result=result,
                chemistry=chemistry,
                validation=validation,
                report=report,
                diagnostics=diagnostics,
            )
        )
    return runs


def plot_pipeline_v3_tvel_heating(runs: list[PipelineV3Run]):
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.0), constrained_layout=True)
    h2_axis = axes[1].twinx()
    colors = ["#2f6f6d", "#b47b20", "#8a2d28", "#4c5f8f"]
    threshold = float(runs[0].scenario.chemistry_threshold_k)
    fuel_limit = float(runs[0].scenario.fuel.melting_temperature_k)
    clad_limit = float(runs[0].scenario.clad.limit_temperature_k)

    for color, run in zip(colors, runs, strict=False):
        time_s = np.asarray(run.result["time_s"], dtype=float)
        fuel = np.asarray(run.result["fuel_center_k"], dtype=float)
        clad = np.asarray(run.result["clad_outer_k"], dtype=float)
        steam = np.asarray(run.result["water_temperature_k"], dtype=float)
        h2_mg_m = np.asarray(run.chemistry["hydrogen_kg_per_m"], dtype=float) * 1e6
        label = _short_label(run.spec.label)
        axes[0].plot(time_s, fuel, color=color, lw=1.8, label=label + ": топливо")
        axes[0].plot(time_s, clad, color=color, lw=1.4, ls="--", label=label + ": W")
        axes[1].plot(time_s, steam, color=color, lw=1.8, label=label + ": пар")
        h2_axis.plot(
            time_s,
            h2_mg_m,
            color=color,
            lw=1.2,
            ls=":",
            label=label + r": \(H_2\)",
        )

    axes[0].axhline(fuel_limit, color="#202020", lw=1.1, ls=":", label="предел HfC")
    axes[0].axhline(clad_limit, color="#6b4e9b", lw=1.1, ls="-.", label="предел W")
    axes[0].set_title("GeN-Foam: нагрев только ТВЭЛа")
    axes[0].set_xlabel("время, с")
    axes[0].set_ylabel("температура, K")
    axes[0].grid(color="#d7d7d7", lw=0.8)
    axes[0].legend(frameon=False, fontsize=7.4, ncol=1)

    axes[1].axhline(threshold, color="#202020", lw=1.1, ls=":", label=r"$T^*_{\mathrm{дис}}$")
    axes[1].set_title("Вода/пар: только поток от стенки")
    axes[1].set_xlabel("время, с")
    axes[1].set_ylabel("температура пара, K")
    h2_axis.set_ylabel(r"\(H_2\), мг/м")
    axes[1].grid(color="#d7d7d7", lw=0.8)
    lines, labels = axes[1].get_legend_handles_labels()
    h2_lines, h2_labels = h2_axis.get_legend_handles_labels()
    axes[1].legend(lines + h2_lines, labels + h2_labels, frameon=False, fontsize=7.4)
    fig.suptitle("V3: длительность импульса без отдельного нагрева пара", fontsize=12)
    return fig


def export_pipeline_v3_artifacts(output_dir: str | Path = "figures") -> list[PipelineV3Run]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 140})
    runs = run_pipeline_v3()
    fig = plot_pipeline_v3_tvel_heating(runs)
    fig.savefig(
        output_path / "pipeline_v3_tvel_heating.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(fig)
    _write_pipeline_v3_tex(output_path / "pipeline_v3_report.tex", runs)
    return runs


def _make_v3_scenario(spec: PipelineV3Spec, fuel: Material, clad: Material) -> Scenario:
    base = build_notebook_baseline_scenario()
    layer = AnnularWaterLayer(
        thickness_m=spec.layer_thickness_m,
        pressure_pa=15.5e6,
        initial_temperature_k=620.0,
        saturation_temperature_k=620.0,
        liquid_density_kg_m3=650.0,
        cp_liquid_j_kg_k=6.0e3,
        latent_heat_j_kg=1.10e6,
        cp_vapor_j_kg_k=2.6e3,
        wall_temperature_cap=True,
    )
    pulse = replace(
        base.pulse,
        energy_j_per_m=BASE_HFC_ENERGY_J_PER_M
        * spec.power_scale
        * spec.pulse_duration_s
        / BASE_PULSE_DURATION_S,
        duration_s=spec.pulse_duration_s,
    )
    scenario = build_annular_water_scenario(
        geometry=base.geometry,
        fuel=base.fuel,
        clad=base.clad,
        pulse=pulse,
        annular_water_layer=layer,
        gap_conductance_w_m2_k=base.gap_conductance_w_m2_k,
        t_end_s=base.t_end_s,
        chemistry_threshold_k=base.chemistry_threshold_k,
        genfoam_case_path=spec.genfoam_case_path,
        name="tvel_wall_heating_v3",
    )
    scenario = make_material_scenario(fuel, clad, pulse.energy_j_per_m, scenario)
    return replace(scenario, pulse=pulse, genfoam_case_path=spec.genfoam_case_path)


def _tvel_heating_diagnostics(
    result: dict[str, Any],
    scenario: Scenario,
    chemistry: dict[str, Any],
) -> dict[str, float | bool]:
    fuel = np.asarray(result["fuel_center_k"], dtype=float)
    clad = np.asarray(result["clad_outer_k"], dtype=float)
    steam = np.asarray(result["water_temperature_k"], dtype=float)
    water_energy = np.asarray(result["water_energy_j_per_m"], dtype=float)
    pulse = np.asarray(result["pulse_energy_j_per_m"], dtype=float)
    h2 = np.asarray(chemistry["hydrogen_kg_per_m"], dtype=float)
    return {
        "max_fuel_k": float(np.max(fuel)),
        "max_clad_k": float(np.max(clad)),
        "max_steam_k": float(np.max(steam)),
        "fuel_margin_k": float(scenario.fuel.melting_temperature_k - np.max(fuel)),
        "clad_margin_k": float(scenario.clad.limit_temperature_k - np.max(clad)),
        "target_reached": bool(np.max(steam) >= scenario.chemistry_threshold_k),
        "reactor_thermal_ok": bool(
            np.max(fuel) < scenario.fuel.melting_temperature_k
            and np.max(clad) < scenario.clad.limit_temperature_k
        ),
        "steam_energy_kj_per_m": float(np.max(water_energy) / 1e3),
        "steam_energy_percent_of_pulse": float(
            100.0 * np.max(water_energy) / max(float(pulse[-1]), 1.0)
        ),
        "peak_h2_mg_per_m": float(np.max(h2) * 1e6),
        "peak_h2_mole_percent": float(np.max(chemistry["h2_mole_fraction"]) * 100.0),
    }


def _material_by_name(materials: list[Material], name: str) -> Material:
    for material in materials:
        if material.name == name:
            return material
    raise ValueError(f"Unknown material: {name}")


def _short_label(label: str) -> str:
    return label.replace(r"\(", "").replace(r"\)", "").split(",")[1].strip()


def _status(run: PipelineV3Run) -> str:
    if run.diagnostics["target_reached"] and run.diagnostics["reactor_thermal_ok"]:
        return "целевой режим достигнут без нарушения тепловых пределов"
    if run.diagnostics["target_reached"]:
        return "паровое окно достигнуто, но реакторная часть перегрета"
    if not run.diagnostics["reactor_thermal_ok"]:
        return "реакторная часть перегрета до достижения парового окна"
    return "пределы соблюдены, но паровое окно не достигнуто"


def _write_pipeline_v3_tex(path: Path, runs: list[PipelineV3Run]) -> None:
    rows = []
    for run in runs:
        diag = run.diagnostics
        rows.append(
            " & ".join(
                [
                    str(run.report["case"]),
                    _format_float(float(run.spec.pulse_duration_s), 2),
                    _format_float(float(run.spec.power_scale), 0),
                    _format_float(float(diag["max_fuel_k"]), 0),
                    _format_float(float(diag["max_clad_k"]), 0),
                    _format_float(float(diag["max_steam_k"]), 0),
                    _format_float(float(diag["steam_energy_percent_of_pulse"]), 4),
                    _format_float(float(diag["peak_h2_mg_per_m"]), 3),
                    _status(run),
                ]
            )
            + r" \\"
        )

    text = rf"""\subsection{{V3: нагрев пара только через ТВЭЛ}}

По требованию физической постановки V3 исключает отдельный нагреватель пара. Вся энергия вводится в топливо GeN-Foam через \texttt{{nuclearFuelPin}}, затем проходит через топливо, зазор, W-оболочку и только после этого попадает в локальный водный слой. Python-часть больше не задает долю импульса, дошедшую до воды. Она интегрирует поток от наружной стенки:
\[
\frac{{dE_w}}{{dt}} = h_{{\mathrm{{eff}}}} A_{{\mathrm{{об}}}}
\max(T_{{\mathrm{{об}}}}-T_w,0),
\qquad
T_w \le T_{{\mathrm{{об}}}}.
\]
Коэффициент \(h_{{\mathrm{{eff}}}}\) выбирается по текущей фазе воды: однофазный нагрев, кипение или перегретый пар; в сухом паре добавляется радиационная поправка W-стенка--пар. Поэтому модель проверяет именно вопрос: может ли нагретый ТВЭЛ сам довести воду или пар до \(T^*_{{\mathrm{{дис}}}}\), не разрушая топливо и оболочку.

\begin{{figure}}[H]
    \centering
    \includegraphics[width=0.88\textwidth]{{figures/pipeline_v3_tvel_heating.png}}
    \caption{{V3 без отдельного нагрева пара: GeN-Foam греет только ТВЭЛ, а вода получает энергию через наружную W-оболочку. Длинный импульс улучшает теплопередачу, но в текущей геометрии целевое паровое окно не открывается без перегрева топлива.}}
    \label{{fig:pipelineV3TvelHeating}}
\end{{figure}}

\begin{{table}}[H]
    \centering
    \caption{{Проверка гипотезы о длительности импульса для нагрева пара через ТВЭЛ.}}
    \label{{tab:pipelineV3TvelHeating}}
    \footnotesize
    \resizebox{{\textwidth}}{{!}}{{%
    \begin{{tabular}}{{@{{}}p{{4.0cm}}rrrrrrrp{{4.8cm}}@{{}}}}
    \hline
    Сценарий & \(\tau_p\), с & \(P/P_0\) & \(T_f^{{\max}}\), K & \(T_W^{{\max}}\), K & \(T_s^{{\max}}\), K & \(\eta_s\), \% & \(m_{{H_2}}\), мг/м & Вывод \\
    \hline
    {chr(10).join(rows)}
    \hline
    \end{{tabular}}
    }}
\end{{table}}

Расчет показывает, почему простое увеличение длительности импульса не является автоматическим решением. Более длинный импульс действительно дает теплу больше времени пройти к W-оболочке и водному слою, но температура пара остается ограничена температурой наружной стенки. В коротком жестком импульсе топливо перегревается раньше, чем оболочка и пар достигают области диссоциации. В растянутом импульсе теплопередача мягче, но целевой уровень \(T_s\approx3273\,\mathrm{{K}}\) все равно не достигается. Следовательно, в текущей геометрии одного ТВЭЛа положительный водородный режим через один только нагрев топлива не получается; для продолжения нужны не отдельный нагреватель пара, а изменение самой теплопередающей геометрии ТВЭЛа, например уменьшение теплового сопротивления зазора, другой радиус/толщина активного слоя или отдельная квалифицированная стенка горячего канала.
"""
    path.write_text(text, encoding="utf-8")
