from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from .cantera_equilibrium import compute_equilibrium_hydrogen
from .genfoam_io import load_genfoam_case
from .pipeline_export import _format_float, repo_relative_path
from .reports import build_scenario_report
from .scenarios import AnnularWaterLayer, Material, PinGeometry, Pulse, Scenario
from .scenarios import build_annular_water_scenario
from .validation import validate_physical_consistency
from .wall_coupled_water import WallHeatTransfer, apply_wall_coupled_water_model
from .water_state import water_energy_for_temperature_j_per_m


BASE_HFC_ENERGY_J_PER_M = 480e3
BASE_PULSE_DURATION_S = 0.20
DELTA_H_DISSOCIATION_J_PER_MOL = 241.93e3
H2_MOLAR_MASS_KG_PER_MOL = 2.01588e-3


@dataclass(frozen=True)
class PipelineV4Spec:
    label: str
    genfoam_case_path: str
    power_scale: float
    pulse_duration_s: float
    role: str


@dataclass(frozen=True)
class PipelineV4Run:
    spec: PipelineV4Spec
    scenario: Scenario
    result: dict[str, Any]
    chemistry: dict[str, Any]
    validation: dict[str, Any]
    report: dict[str, float | str | bool]
    diagnostics: dict[str, float | bool]


def pipeline_v4_specs() -> list[PipelineV4Spec]:
    return [
        PipelineV4Spec(
            label=r"керметный слой, \(20P_0\)",
            genfoam_case_path=str(
                repo_relative_path(
                    "GENFOAM_V4_CERMET_P20_PATH",
                    "data/genfoam/tvel-structure-v4/cermet_annular_p20",
                )
            ),
            power_scale=20.0,
            pulse_duration_s=1.0,
            role="контроль: топливо и оболочка целы, пар ниже целевого окна",
        ),
        PipelineV4Spec(
            label=r"керметный слой, \(28P_0\)",
            genfoam_case_path=str(
                repo_relative_path(
                    "GENFOAM_V4_CERMET_P28_PATH",
                    "data/genfoam/tvel-structure-v4/cermet_annular_p28",
                )
            ),
            power_scale=28.0,
            pulse_duration_s=1.0,
            role="кандидат: пар проходит порог при сохранении тепловых пределов",
        ),
    ]


def run_pipeline_v4() -> list[PipelineV4Run]:
    runs: list[PipelineV4Run] = []
    for spec in pipeline_v4_specs():
        scenario = _make_v4_scenario(spec)
        result = load_genfoam_case(spec.genfoam_case_path, scenario)
        result = apply_wall_coupled_water_model(
            result,
            scenario,
            WallHeatTransfer(max_substep_s=5.0e-4),
        )
        chemistry = compute_equilibrium_hydrogen(result, scenario)
        validation = validate_physical_consistency(result)
        report = build_scenario_report(spec.label, result, validation, chemistry)
        diagnostics = _structured_tvel_diagnostics(result, scenario, chemistry)
        runs.append(
            PipelineV4Run(
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


def plot_pipeline_v4_structured_tvel(runs: list[PipelineV4Run]):
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.0), constrained_layout=True)
    h2_axis = axes[1].twinx()
    colors = ["#4d7358", "#9f442d"]
    threshold = float(runs[0].scenario.chemistry_threshold_k)
    fuel_limit = float(runs[0].scenario.fuel.limit_temperature_k)
    clad_limit = float(runs[0].scenario.clad.limit_temperature_k)

    for color, run in zip(colors, runs, strict=False):
        time_s = np.asarray(run.result["time_s"], dtype=float)
        fuel = np.asarray(run.result["fuel_center_k"], dtype=float)
        clad = np.asarray(run.result["clad_outer_k"], dtype=float)
        steam = np.asarray(run.result["water_temperature_k"], dtype=float)
        h2_mg_m = np.asarray(run.chemistry["hydrogen_kg_per_m"], dtype=float) * 1e6
        label = run.spec.label.replace(r"\(", "").replace(r"\)", "")
        axes[0].plot(time_s, fuel, color=color, lw=1.8, label=label + ": топливо")
        axes[0].plot(time_s, clad, color=color, lw=1.4, ls="--", label=label + ": W")
        axes[1].plot(time_s, steam, color=color, lw=1.8, label=label + ": пар")
        h2_axis.plot(
            time_s,
            h2_mg_m,
            color=color,
            lw=1.25,
            ls=":",
            label=label + r": \(H_2\)",
        )

    axes[0].axhline(fuel_limit, color="#202020", lw=1.1, ls=":", label="предел кермета")
    axes[0].axhline(clad_limit, color="#6b4e9b", lw=1.1, ls="-.", label="предел W")
    axes[0].set_title("GeN-Foam: измененная структура твэла")
    axes[0].set_xlabel("время, с")
    axes[0].set_ylabel("температура, K")
    axes[0].grid(color="#d7d7d7", lw=0.8)
    axes[0].legend(frameon=False, fontsize=7.4)

    axes[1].axhline(threshold, color="#202020", lw=1.1, ls=":", label=r"$T^*_{\mathrm{дис}}$")
    axes[1].set_title("Cantera: равновесный водород")
    axes[1].set_xlabel("время, с")
    axes[1].set_ylabel("температура воды/пара, K")
    h2_axis.set_ylabel(r"\(H_2\), мг/м")
    axes[1].grid(color="#d7d7d7", lw=0.8)
    lines, labels = axes[1].get_legend_handles_labels()
    h2_lines, h2_labels = h2_axis.get_legend_handles_labels()
    axes[1].legend(lines + h2_lines, labels + h2_labels, frameon=False, fontsize=7.4)
    fig.suptitle("V4: кольцевой высокотеплопроводный слой без отдельного нагрева пара", fontsize=12)
    return fig


def export_pipeline_v4_artifacts(output_dir: str | Path = "figures") -> list[PipelineV4Run]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 140})
    runs = run_pipeline_v4()
    fig = plot_pipeline_v4_structured_tvel(runs)
    fig.savefig(
        output_path / "pipeline_v4_structured_tvel.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(fig)
    _write_pipeline_v4_tex(output_path / "pipeline_v4_report.tex", runs)
    return runs


def _make_v4_scenario(spec: PipelineV4Spec) -> Scenario:
    geometry = PinGeometry(
        fuel_inner_radius_m=3.40e-3,
        fuel_radius_m=4.00e-3,
        gap_outer_radius_m=4.005e-3,
        clad_outer_radius_m=4.20e-3,
        n_fuel=12,
        n_clad=6,
    )
    fuel = Material(
        "W-carbide cermet surrogate",
        conductivity_w_m_k=90.0,
        volumetric_heat_capacity_j_m3_k=4.2e6,
        melting_temperature_k=3695.0,
    )
    clad = Material("Tungsten", 120.0, 2.6e6, 3695.0)
    layer = AnnularWaterLayer(
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
    pulse = Pulse(
        energy_j_per_m=BASE_HFC_ENERGY_J_PER_M
        * spec.power_scale
        * spec.pulse_duration_s
        / BASE_PULSE_DURATION_S,
        duration_s=spec.pulse_duration_s,
    )
    return build_annular_water_scenario(
        geometry=geometry,
        fuel=fuel,
        clad=clad,
        pulse=pulse,
        annular_water_layer=layer,
        gap_conductance_w_m2_k=1.0e6,
        t_end_s=1.25,
        chemistry_threshold_k=3273.15,
        genfoam_case_path=spec.genfoam_case_path,
        name="structured_tvel_v4",
    )


def _structured_tvel_diagnostics(
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
    target_energy_j_per_m = water_energy_for_temperature_j_per_m(
        scenario.chemistry_threshold_k,
        scenario.water,
    )
    dissociation_energy_j_per_m = max(0.0, float(np.max(water_energy)) - target_energy_j_per_m)
    h2_energy_cap_mg_per_m = (
        dissociation_energy_j_per_m
        / DELTA_H_DISSOCIATION_J_PER_MOL
        * H2_MOLAR_MASS_KG_PER_MOL
        * 1e6
    )
    peak_h2_mg_per_m = float(np.max(h2) * 1e6)
    return {
        "max_fuel_k": float(np.max(fuel)),
        "max_clad_k": float(np.max(clad)),
        "max_steam_k": float(np.max(steam)),
        "fuel_margin_k": float(scenario.fuel.limit_temperature_k - np.max(fuel)),
        "clad_margin_k": float(scenario.clad.limit_temperature_k - np.max(clad)),
        "target_reached": bool(np.max(steam) >= scenario.chemistry_threshold_k),
        "thermal_ok": bool(
            np.max(fuel) < scenario.fuel.limit_temperature_k
            and np.max(clad) < scenario.clad.limit_temperature_k
        ),
        "steam_energy_kj_per_m": float(np.max(water_energy) / 1e3),
        "steam_energy_percent_of_pulse": float(
            100.0 * np.max(water_energy) / max(float(pulse[-1]), 1.0)
        ),
        "required_energy_to_threshold_kj_per_m": target_energy_j_per_m / 1e3,
        "dissociation_energy_cap_kj_per_m": dissociation_energy_j_per_m / 1e3,
        "peak_h2_mg_per_m": peak_h2_mg_per_m,
        "h2_energy_cap_mg_per_m": h2_energy_cap_mg_per_m,
        "h2_admissible_mg_per_m": min(peak_h2_mg_per_m, h2_energy_cap_mg_per_m),
        "peak_h2_mole_percent": float(np.max(chemistry["h2_mole_fraction"]) * 100.0),
    }


def _status(run: PipelineV4Run) -> str:
    if run.diagnostics["target_reached"] and run.diagnostics["thermal_ok"]:
        return "кандидат: окно достигнуто без превышения принятого теплового предела"
    if run.diagnostics["target_reached"]:
        return "окно достигнуто только при нарушении тепловых пределов"
    if not run.diagnostics["thermal_ok"]:
        return "структура перегрета до открытия окна"
    return "пределы соблюдены, но окно не открыто"


def _write_pipeline_v4_tex(path: Path, runs: list[PipelineV4Run]) -> None:
    rows = []
    for run in runs:
        diag = run.diagnostics
        rows.append(
            " & ".join(
                [
                    rf"\({_format_float(float(run.spec.power_scale), 0)}P_0\)",
                    _format_float(float(diag["max_fuel_k"]), 0),
                    _format_float(float(diag["max_clad_k"]), 0),
                    _format_float(float(diag["max_steam_k"]), 0),
                    _format_float(float(diag["fuel_margin_k"]), 0),
                    _format_float(float(diag["clad_margin_k"]), 0),
                    _format_float(float(diag["steam_energy_kj_per_m"]), 2),
                    _format_float(float(diag["peak_h2_mg_per_m"]), 2),
                    _format_float(float(diag["h2_admissible_mg_per_m"]), 2),
                    _status(run),
                ]
            )
            + r" \\"
        )

    text = rf"""\subsection{{V4: изменение структуры твэла}}

Расчет V4 проверяет не увеличение мощности в прежнем твэле, а изменение пути теплопередачи. Топливо заменено расчетным кольцевым высокотеплопроводным керметным слоем \(r=3.40\text{{--}}4.00\,\mathrm{{мм}}\). Внутренняя граница \(r=3.40\,\mathrm{{мм}}\) задана адиабатической как расчетное приближение инертного внутреннего сердечника или симметричного эквивалента; теплоотвод через нее в этой версии не моделируется. Между активным слоем и оболочкой оставлен почти связанный контакт \(h_g=10^6\,\mathrm{{Вт/(м^2\,K)}}\), W-оболочка уменьшена до \(0.195\,\mathrm{{мм}}\), а локальный слой воды у стенки принят равным \(100\,\mu\mathrm{{m}}\). Энергия по-прежнему вводится только в топливо GeN-Foam; отдельного нагревателя пара нет. Обозначение \(P_0\) здесь сохраняет нормировку V3: \(1P_0\) соответствует \(480\,\mathrm{{кДж/м}}\) за \(0.2\,\mathrm{{с}}\).

\begin{{figure}}[H]
    \centering
    \includegraphics[width=0.88\textwidth]{{figures/pipeline_v4_structured_tvel.png}}
    \caption{{V4: кольцевой высокотеплопроводный слой снижает радиальный перегрев топлива и позволяет наружной W-стенке открыть температурное окно для воды/пара. Cantera дает равновесную оценку \(H_2\), а не извлекаемую массу продукта.}}
    \label{{fig:pipelineV4StructuredTvel}}
\end{{figure}}

\begin{{table}}[H]
    \centering
    \caption{{Проверка измененной структуры твэла: нагрев только через топливо.}}
    \label{{tab:pipelineV4StructuredTvel}}
    \footnotesize
    \begin{{tabularx}}{{\textwidth}}{{@{{}}crrrrrrrrX@{{}}}}
    \toprule
    \(P/P_0\) & \(T_f^{{\max}}\), K & \(T_W^{{\max}}\), K & \(T_s^{{\max}}\), K & \(M_f\), K & \(M_W\), K & \(E'_w\), кДж/м & \(m_{{H_2}}^{{eq}}\), мг/м & \(m_{{H_2}}^{{\mathrm{{lim}}}}\), мг/м & Статус \\
    \midrule
    {chr(10).join("    " + row for row in rows)}
    \bottomrule
    \end{{tabularx}}
\end{{table}}

Для \(H_2\) в таблице разделены две величины. \(m_{{H_2}}^{{eq}}\) -- равновесный индикатор Cantera при достигнутых \(T_s\) и \(p_s\). Энергетически допустимая верхняя оценка дополнительно ограничена остатком после нагрева воды до принятого порога:
\[
m_{{H_2}}^{{\mathrm{{lim}}}}=
\min\left(
m_{{H_2}}^{{eq}},
\frac{{Q_{{\mathrm{{diss}}}}^{{\max}}}}{{\Delta H_{{\mathrm{{diss}}}}}}M_{{H_2}}
\right),
\qquad
Q_{{\mathrm{{diss}}}}^{{\max}}=\max\left(0,E'_w-E'_{{w,*}}\right).
\]

Положительный расчетный режим возникает только после изменения геометрии теплопередачи и уменьшения локальной массы воды у стенки. При \(20P_0\) структура остается холоднее пределов, но пар не достигает \(T^*_{{\mathrm{{дис}}}}\). При \(28P_0\) максимум пара составляет около \(3410\,\mathrm{{K}}\), максимум топлива около \(3470\,\mathrm{{K}}\), а W-оболочки около \(3430\,\mathrm{{K}}\). Принятый предел \(3695\,\mathrm{{K}}\) является расчетным материаловым ориентиром, привязанным к температуре плавления W и W-карбидного суррогата; это не эксплуатационный предел с ресурсным запасом. Поэтому в рамках текущей тепловой модели появляется только кандидатный режим образования \(H_2\). Он не является проектом реактора: керметный слой, W-стенка в паре, механика тонкой оболочки, нейтроника, радиационная граница и химическая кинетика требуют отдельной квалификации.
"""
    path.write_text(text, encoding="utf-8")
