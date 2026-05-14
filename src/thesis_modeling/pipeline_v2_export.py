from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from .cantera_equilibrium import (
    compute_equilibrium_hydrogen,
    compute_python_hydrogen_proxy,
)
from .fallback_physics import simulate_python_fallback
from .genfoam_io import load_genfoam_case
from .material_screening import candidate_claddings, candidate_fuels, make_material_scenario
from .pipeline_export import (
    build_notebook_baseline_scenario,
    repo_relative_path,
    _format_float,
)
from .reports import build_scenario_report
from .scenarios import Material, Scenario
from .validation import validate_physical_consistency
from .wall_coupled_water import apply_wall_coupled_water_model


@dataclass(frozen=True)
class PipelineV2Spec:
    label: str
    fuel_name: str
    clad_name: str
    pulse_energy_j_per_m: float
    genfoam_case_path: str
    role: str


@dataclass(frozen=True)
class PipelineV2Run:
    spec: PipelineV2Spec
    scenario: Scenario
    result: dict[str, Any]
    chemistry: dict[str, Any]
    validation: dict[str, Any]
    report: dict[str, float | str | bool]


def pipeline_v2_specs() -> list[PipelineV2Spec]:
    return [
        PipelineV2Spec(
            label=r"\(\mathrm{ZrC}\)--W, исследовательский суррогат",
            fuel_name="ZrC surrogate",
            clad_name="Tungsten",
            pulse_energy_j_per_m=520e3,
            genfoam_case_path=str(repo_relative_path(
                "GENFOAM_V2_ZRC_W_PATH",
                "data/genfoam/materials-v2/zrc_w",
            )),
            role="более правдоподобная ZrC-центричная ветка; наружный W не квалифицирован по пару",
        ),
        PipelineV2Spec(
            label=r"\(\mathrm{HfC}\)--W, тепловой верхний контрфакт",
            fuel_name="HfC surrogate",
            clad_name="Tungsten",
            pulse_energy_j_per_m=480e3,
            genfoam_case_path=str(repo_relative_path(
                "GENFOAM_V2_HFC_W_PATH",
                "data/genfoam/materials-v2/hfc_w",
            )),
            role="оптимистический тепловой предел; материал не квалифицирован по нейтронике и пару",
        ),
    ]


def _material_by_name(materials: list[Material], name: str) -> Material:
    for material in materials:
        if material.name == name:
            return material
    raise ValueError(f"Unknown material: {name}")


def _format_bool(value: bool) -> str:
    return "да" if value else "нет"


def run_pipeline_v2(*, allow_python_fallback: bool = False) -> list[PipelineV2Run]:
    base = build_notebook_baseline_scenario()
    fuels = candidate_fuels()
    claddings = candidate_claddings()
    runs: list[PipelineV2Run] = []
    for spec in pipeline_v2_specs():
        scenario = make_material_scenario(
            _material_by_name(fuels, spec.fuel_name),
            _material_by_name(claddings, spec.clad_name),
            pulse_energy_j_per_m=spec.pulse_energy_j_per_m,
            base=base,
        )
        scenario = replace(scenario, genfoam_case_path=spec.genfoam_case_path)
        try:
            result = load_genfoam_case(spec.genfoam_case_path, scenario)
            result = apply_wall_coupled_water_model(result, scenario)
            chemistry = compute_equilibrium_hydrogen(result, scenario)
        except (FileNotFoundError, NotADirectoryError) as exc:
            if not allow_python_fallback:
                raise
            result = simulate_python_fallback(scenario)
            result["fallback_reason"] = str(exc)
            chemistry = compute_python_hydrogen_proxy(result, scenario)
        validation = validate_physical_consistency(result)
        report = build_scenario_report(spec.label, result, validation, chemistry)
        runs.append(
            PipelineV2Run(
                spec=spec,
                scenario=scenario,
                result=result,
                chemistry=chemistry,
                validation=validation,
                report=report,
            )
        )
    return runs


def plot_pipeline_v2_material_window(runs: list[PipelineV2Run]):
    labels = [
        run.spec.label.replace(r"\(", "")
        .replace(r"\)", "")
        .replace(r"\mathrm{", "")
        .replace("}", "")
        .split(",")[0]
        for run in runs
    ]
    threshold = float(runs[0].report["chemistry_threshold_k"])
    margins = [float(run.report["max_gas_k"]) - threshold for run in runs]
    colors = [
        "#2f6f6d" if bool(run.report["threshold_before_material_limits"]) else "#a95743"
        for run in runs
    ]

    fig, ax = plt.subplots(figsize=(6.8, 3.8), constrained_layout=True)
    ax.bar(labels, margins, color=colors, width=0.58)
    for x, value in enumerate(margins):
        ax.text(
            x,
            value - 80.0,
            f"{value:.0f} K",
            ha="center",
            va="top",
            fontsize=9,
        )
    ax.axhline(0.0, color="#202020", lw=1.2, ls="--")
    ax.text(
        0.98,
        0.92,
        rf"$0 = T^*_{{\mathrm{{дис}}}}={threshold:.0f}$ K",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8.5,
        bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.92},
    )
    bottom = min(margins) * 1.12
    ax.set_ylim(bottom, max(120.0, -0.05 * bottom))
    ax.set_ylabel(r"$\Delta T=T_s^{\max}-T^*_{\mathrm{дис}}$, K")
    ax.set_title("V2: дефицит до принятого порога")
    ax.grid(axis="y", color="#d6d6d6", lw=0.8)
    ax.tick_params(axis="x", rotation=0)
    return fig


def _run_class(run: PipelineV2Run) -> str:
    if bool(run.report["threshold_before_material_limits"]):
        return "тепловое окно достигнуто"
    if bool(run.report["below_temperature_limits"]):
        return "материалы целы, окно ниже порога"
    return "ограничения нарушены до окна"


def _source_summary(runs: list[PipelineV2Run]) -> str:
    sources = {str(run.result.get("thermal_source", "")) for run in runs}
    if sources == {"genfoam"}:
        return (
            "Тепловая часть во всех строках взята из отдельных расчетов "
            r"GeN-Foam \texttt{nuclearFuelPin} с отключением мощности после "
            r"\(0.2\,\mathrm{с}\)."
        )
    if sources == {"python_fallback"}:
        return (
            r"В этом прогоне использован резервный расчет \texttt{python\_fallback}: тепловые ряды "
            "получены трехузловой моделью, потому что пригодные для этих "
            "материальных сценариев ряды GeN-Foam не были доступны."
        )
    return "В таблице смешаны внешние GeN-Foam-ряды и резервный расчет Python."


def _chemistry_summary(runs: list[PipelineV2Run]) -> str:
    if all(bool(run.chemistry.get("uses_cantera")) for run in runs):
        return r"\(m_{H_2}^{eq}\) по равновесному расчету Cantera."
    return r"\(m_{H_2}^{proxy}\) по пороговой оценке без Cantera."


def _write_pipeline_v2_tex(path: Path, runs: list[PipelineV2Run]) -> None:
    rows = []
    for run in runs:
        report = run.report
        rows.append(
            " & ".join(
                [
                    str(report["case"]),
                    _format_float(float(report["pulse_kj_per_m"]), 0),
                    _format_float(float(report["max_gas_k"]), 0),
                    _format_bool(bool(report["threshold_before_material_limits"])),
                    _run_class(run),
                    run.spec.role,
                ]
            )
            + r" \\"
        )
    source_summary = _source_summary(runs)
    chemistry_summary = _chemistry_summary(runs)

    text = rf"""\subsection{{Материаловедческий отбор для парового окна}}

Отборочный расчет отвечает уже не на вопрос о штатной циркониевой оболочке, а на вопрос о том, какой класс материалов нужен для реакторной схемы, способной подвести энергию к тонкому слою воды у оболочки и открыть путь к ненулевому выходу \(H_2\). Входами остаются геометрия одного метра твэла, давление \(15.5\,\mathrm{{МПа}}\), толщина водного слоя и импульс \(E_{{\mathrm{{вв}}}}\). Основные выходы не меняются: \(T_s^{{\max}}\), запас топлива и оболочки до пределов и {chemistry_summary}

{source_summary}

Этот отборочный слой не заменяет химико-механическую квалификацию материалов. \(\mathrm{{ZrC}}\)-центричная ветка введена как более правдоподобное исследовательское направление после отсева \(\mathrm{{UO_2}}\), \(\mathrm{{UN}}\), \(\mathrm{{UC}}\), Zircaloy, Mo и SiC/SiC. \(\mathrm{{HfC}}\)--W оставлен как оптимистический тепловой контрфакт. В текущем импульсном расчете GeN-Foam он также не открывает высокотемпературное водно-паровое окно; это полезный отрицательный результат, а не предложение материала из-за гафния и парового окисления вольфрама \cite{{UshakovCarbides2019,PetersonZrC2023,SabourinTungstenSteam2011}}.

\begin{{figure}}[H]
    \centering
    \includegraphics[width=0.74\textwidth]{{figures/pipeline_v2_material_window.png}}
    \caption{{Отдельные расчеты GeN-Foam для новых материалов: дефицит максимума водно-парового слоя до принятого порога заметной равновесной доли \(H_2\). Оба варианта остаются далеко ниже целевого уровня.}}
    \label{{fig:pipelineV2MaterialWindow}}
\end{{figure}}

\begin{{table}}[H]
    \centering
    \caption{{Отборочные сценарии для новой материальной структуры.}}
    \label{{tab:pipelineV2MaterialScenarios}}
    \footnotesize
    \setlength{{\tabcolsep}}{{3pt}}
    \renewcommand{{\arraystretch}}{{1.12}}
    \begin{{tabularx}}{{\textwidth}}{{@{{}}LYYZLL@{{}}}}
    \toprule
    Сценарий & \(E_{{\mathrm{{вв}}}}\), кДж/м & \(T_s^{{\max}}\), K & Окно до пределов & Класс результата & Роль в дипломе \\
    \midrule
    {chr(10).join(rows)}
    \bottomrule
    \end{{tabularx}}
\end{{table}}

Инженерная трактовка такого расчета остается умеренной: цель диплома -- найти расчетную область, где реакторная система может получить высокотемпературный пар и ненулевую равновесную оценку \(H_2\). Текущий GeN-Foam-прогон показывает, что одна замена материалов без изменения теплогидравлической схемы и подвода энергии не решает задачу. Поэтому следующий расчетный шаг должен менять не только материал, но и геометрию теплопередачи, длительность или пространственную концентрацию энерговыделения.
"""
    path.write_text(text, encoding="utf-8")


def export_pipeline_v2_artifacts(
    output_dir: str | Path = "figures",
    *,
    allow_python_fallback: bool = False,
) -> list[PipelineV2Run]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 140})
    runs = run_pipeline_v2(allow_python_fallback=allow_python_fallback)
    fig = plot_pipeline_v2_material_window(runs)
    fig.savefig(output_path / "pipeline_v2_material_window.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    _write_pipeline_v2_tex(output_path / "pipeline_v2_report.tex", runs)
    return runs
