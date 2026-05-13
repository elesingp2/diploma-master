from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

from .scenarios import Scenario


FUEL_COLOR = "#d8903d"
GAP_COLOR = "#f7f7f2"
CLAD_COLOR = "#9aa8b3"
WATER_COLOR = "#8fd0f2"
GAS_LAYER_COLOR = "#f4d03f"
LINE_COLORS = {
    "fuel_center": "#7a1f1f",
    "fuel_surface": "#d95f02",
    "clad_outer": "#1b7837",
    "water": "#2166ac",
}


def _style_axis(ax) -> None:
    ax.grid(True, color="#000000", alpha=0.14, lw=0.7)
    ax.tick_params(direction="in", top=True, right=True)


def _fluid_label(scenario: Scenario) -> str:
    if scenario.annular_water_layer is not None:
        return "вода / пар у оболочки"
    return "газовая прослойка" if scenario.steam_layer is not None else "вода / пар"


def _mark_material_regions(ax, scenario: Scenario) -> None:
    geometry = scenario.geometry
    ax.axvspan(0.0, geometry.fuel_radius_m * 1e3, color=FUEL_COLOR, alpha=0.14)
    ax.axvspan(
        geometry.fuel_radius_m * 1e3,
        geometry.gap_outer_radius_m * 1e3,
        color=GAP_COLOR,
        alpha=0.7,
    )
    ax.axvspan(
        geometry.gap_outer_radius_m * 1e3,
        geometry.clad_outer_radius_m * 1e3,
        color=CLAD_COLOR,
        alpha=0.18,
    )
    if scenario.steam_layer is not None:
        ax.axvspan(
            geometry.clad_outer_radius_m * 1e3,
            (geometry.clad_outer_radius_m + scenario.steam_layer.thickness_m) * 1e3,
            color=GAS_LAYER_COLOR,
            alpha=0.24,
        )
    if scenario.annular_water_layer is not None:
        ax.axvspan(
            geometry.clad_outer_radius_m * 1e3,
            (
                geometry.clad_outer_radius_m
                + scenario.annular_water_layer.thickness_m
            )
            * 1e3,
            color=WATER_COLOR,
            alpha=0.24,
        )
    for radius, label in [
        (geometry.fuel_radius_m * 1e3, "топливо"),
        (geometry.gap_outer_radius_m * 1e3, "зазор"),
        (geometry.clad_outer_radius_m * 1e3, "оболочка"),
    ]:
        ax.axvline(radius, color="#2f3542", lw=0.8, alpha=0.45)
        ax.text(
            radius,
            0.98,
            label,
            transform=ax.get_xaxis_transform(),
            ha="right",
            va="top",
            rotation=90,
            fontsize=8,
            color="#2f3542",
        )
    if scenario.steam_layer is not None:
        gas_outer_radius_mm = (
            geometry.clad_outer_radius_m + scenario.steam_layer.thickness_m
        ) * 1e3
        ax.axvline(gas_outer_radius_mm, color="#8c6d1f", lw=0.9, alpha=0.7)
        ax.text(
            gas_outer_radius_mm,
            0.98,
            "газ",
            transform=ax.get_xaxis_transform(),
            ha="left",
            va="top",
            rotation=90,
            fontsize=8,
            color="#4d3d00",
        )
    if scenario.annular_water_layer is not None:
        water_outer_radius_mm = (
            geometry.clad_outer_radius_m + scenario.annular_water_layer.thickness_m
        ) * 1e3
        ax.axvline(water_outer_radius_mm, color="#2166ac", lw=0.9, alpha=0.7)
        ax.text(
            water_outer_radius_mm,
            0.98,
            "вода",
            transform=ax.get_xaxis_transform(),
            ha="left",
            va="top",
            rotation=90,
            fontsize=8,
            color="#17456f",
        )


def _mark_pulse_end(ax, result: dict[str, np.ndarray]) -> None:
    scenario = result["scenario"]
    pulse_end = scenario.pulse.duration_s
    ax.axvline(pulse_end, color="#111827", lw=1.0, ls="--", alpha=0.45)
    ax.text(
        pulse_end,
        0.98,
        "конец импульса",
        transform=ax.get_xaxis_transform(),
        ha="left",
        va="top",
        rotation=90,
        fontsize=8,
        color="#111827",
    )


def _draw_reference_level(
    ax,
    y_value: float,
    *,
    label: str,
    color: str,
    style: str,
) -> str | None:
    y_min, y_max = ax.get_ylim()
    if y_min <= y_value <= y_max:
        ax.axhline(y_value, color=color, ls=style, lw=1.15, label=label)
        return None
    return f"{label}: {y_value:.0f} K"


def plot_pin_cross_section(scenario: Scenario, ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(6.2, 5.2))

    geometry = scenario.geometry
    layer_outer_radius_mm = None
    if scenario.steam_layer is not None:
        layer_outer_radius_mm = (
            geometry.clad_outer_radius_m + scenario.steam_layer.thickness_m
        ) * 1e3
    if scenario.annular_water_layer is not None:
        layer_outer_radius_mm = (
            geometry.clad_outer_radius_m + scenario.annular_water_layer.thickness_m
        ) * 1e3
    water_outer_radius_mm = geometry.clad_outer_radius_m * 1e3 * 1.42
    fuel_radius_mm = geometry.fuel_radius_m * 1e3
    gap_outer_radius_mm = geometry.gap_outer_radius_m * 1e3
    clad_outer_radius_mm = geometry.clad_outer_radius_m * 1e3

    layers = [
        (water_outer_radius_mm, WATER_COLOR, "вода / пар"),
    ]
    if layer_outer_radius_mm is not None:
        if scenario.annular_water_layer is not None:
            layers.append((layer_outer_radius_mm, WATER_COLOR, "слой воды"))
        else:
            layers.append((layer_outer_radius_mm, GAS_LAYER_COLOR, "газовая прослойка"))
    layers.extend(
        [
            (clad_outer_radius_mm, CLAD_COLOR, "оболочка Zr"),
            (gap_outer_radius_mm, GAP_COLOR, "газовый зазор"),
            (fuel_radius_mm, FUEL_COLOR, "топливо UO2"),
        ]
    )
    for radius, color, _ in layers:
        ax.add_patch(
            Circle(
                (0.0, 0.0),
                radius,
                facecolor=color,
                edgecolor="#27313a",
                lw=1.2,
            )
        )

    ax.add_patch(
        Circle((0.0, 0.0), fuel_radius_mm, facecolor="none", edgecolor="#6b3f16", lw=1.6)
    )
    ax.add_patch(
        Circle(
            (0.0, 0.0),
            gap_outer_radius_mm,
            facecolor="none",
            edgecolor="#6b7280",
            lw=1.2,
        )
    )
    ax.add_patch(
        Circle(
            (0.0, 0.0),
            clad_outer_radius_mm,
            facecolor="none",
            edgecolor="#3d4852",
            lw=1.6,
        )
    )
    if layer_outer_radius_mm is not None:
        ax.add_patch(
            Circle(
                (0.0, 0.0),
                layer_outer_radius_mm,
                facecolor="none",
                edgecolor="#8c6d1f",
                lw=1.8,
            )
        )

    ax.text(
        0.0,
        0.0,
        "UO2\nтопливо",
        ha="center",
        va="center",
        fontsize=10,
        weight="bold",
    )
    ax.annotate(
        "газовый\nзазор",
        xy=(gap_outer_radius_mm, 0.0),
        xytext=(water_outer_radius_mm * 1.08, water_outer_radius_mm * 0.55),
        arrowprops={"arrowstyle": "->", "lw": 1.0, "color": "#303841"},
        ha="left",
        va="center",
        fontsize=9,
    )
    ax.annotate(
        "оболочка Zr",
        xy=(clad_outer_radius_mm, 0.0),
        xytext=(water_outer_radius_mm * 1.08, 0.0),
        arrowprops={"arrowstyle": "->", "lw": 1.0, "color": "#303841"},
        ha="left",
        va="center",
        fontsize=9,
    )
    ax.annotate(
        "вода / пар",
        xy=(water_outer_radius_mm * 0.92, -water_outer_radius_mm * 0.25),
        xytext=(water_outer_radius_mm * 1.08, -water_outer_radius_mm * 0.58),
        arrowprops={"arrowstyle": "->", "lw": 1.0, "color": "#303841"},
        ha="left",
        va="center",
        fontsize=9,
    )
    if layer_outer_radius_mm is not None and scenario.steam_layer is not None:
        ax.annotate(
            f"газовая прослойка\nδ = {scenario.steam_layer.thickness_m * 1e6:.0f} мкм",
            xy=(layer_outer_radius_mm, layer_outer_radius_mm * 0.18),
            xytext=(-water_outer_radius_mm * 1.52, water_outer_radius_mm * 0.82),
            arrowprops={"arrowstyle": "->", "lw": 1.0, "color": "#303841"},
            ha="left",
            va="center",
            fontsize=9,
        )
    if layer_outer_radius_mm is not None and scenario.annular_water_layer is not None:
        ax.annotate(
            f"слой воды\nδ = {scenario.annular_water_layer.thickness_m * 1e6:.0f} мкм",
            xy=(layer_outer_radius_mm, layer_outer_radius_mm * 0.18),
            xytext=(-water_outer_radius_mm * 1.52, water_outer_radius_mm * 0.82),
            arrowprops={"arrowstyle": "->", "lw": 1.0, "color": "#303841"},
            ha="left",
            va="center",
            fontsize=9,
        )

    ax.text(
        -water_outer_radius_mm * 1.47,
        -water_outer_radius_mm * 1.43,
        f"Rf = {fuel_radius_mm:.2f} мм\n"
        f"зазор = {(gap_outer_radius_mm - fuel_radius_mm) * 1e3:.0f} мкм\n"
        f"Rоб = {clad_outer_radius_mm:.2f} мм",
        ha="left",
        va="bottom",
        fontsize=8.5,
        bbox={"facecolor": "white", "edgecolor": "#c7c7c7", "alpha": 0.88},
    )
    ax.set_title("Расчетная геометрия ТВЭЛа")
    ax.set_aspect("equal")
    limit = water_outer_radius_mm * 1.65
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_xlabel("x, mm")
    ax.set_ylabel("y, mm")
    _style_axis(ax)
    return ax


def plot_temperature_history(result: dict[str, np.ndarray], ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.5))
    t = result["time_s"]
    scenario = result["scenario"]
    fluid_label = _fluid_label(scenario)
    ax.plot(
        t,
        result["fuel_center_k"],
        color=LINE_COLORS["fuel_center"],
        lw=2.0,
        label="центр топлива",
    )
    ax.plot(
        t,
        result["fuel_surface_k"],
        color=LINE_COLORS["fuel_surface"],
        lw=2.0,
        label="поверхность топлива",
    )
    ax.plot(
        t,
        result["clad_outer_k"],
        color=LINE_COLORS["clad_outer"],
        lw=2.0,
        label="наружная оболочка",
    )
    ax.plot(
        t,
        result["water_temperature_k"],
        color=LINE_COLORS["water"],
        lw=2.0,
        label=fluid_label,
    )
    temperature_stack = np.vstack(
        [
            result["fuel_center_k"],
            result["fuel_surface_k"],
            result["clad_outer_k"],
            result["water_temperature_k"],
            np.full_like(t, scenario.water.saturation_temperature_k),
        ]
    )
    data_min = float(np.min(temperature_stack))
    data_max = float(np.max(temperature_stack))
    margin = max(15.0, 0.16 * (data_max - data_min))
    ax.set_ylim(
        max(0.0, data_min - margin),
        data_max + margin,
    )
    out_of_scale = []
    for item in [
        (
            scenario.water.saturation_temperature_k,
            "начальная T слоя" if scenario.steam_layer is not None else "Tsat воды",
            "#2166ac",
            ":",
        ),
        (
            scenario.clad.limit_temperature_k,
            f"предел оболочки {scenario.clad.name}",
            LINE_COLORS["clad_outer"],
            "--",
        ),
        (
            scenario.chemistry_threshold_k,
            r"$T^*_{\mathrm{дис}}$",
            "#542788",
            "-.",
        ),
    ]:
        label = _draw_reference_level(
            ax,
            item[0],
            label=item[1],
            color=item[2],
            style=item[3],
        )
        if label is not None:
            out_of_scale.append(label)
    if out_of_scale:
        ax.text(
            0.99,
            0.98,
            "выше шкалы:\n" + "\n".join(out_of_scale),
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=8.0,
            color="#253044",
            bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.92},
        )
    _mark_pulse_end(ax, result)
    ax.set_title("V1: температуры GeN-Foam, рабочая шкала")
    ax.set_xlabel("время, с")
    ax.set_ylabel("температура, K")
    _style_axis(ax)
    ax.legend(frameon=True, fontsize=8.0, ncol=2)
    return ax


def plot_radial_temperature_profiles(
    result: dict[str, np.ndarray],
    sample_times_s: list[float] | tuple[float, ...] | None = None,
    ax=None,
):
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.5))

    scenario = result["scenario"]
    time = result["time_s"]
    radius_mm = result["r_m"] * 1e3
    profiles = result["temperature_profile_k"]
    if sample_times_s is None:
        sample_times_s = [
            0.0,
            scenario.pulse.duration_s,
            0.5,
            2.0,
            10.0,
            float(time[-1]),
        ]

    _mark_material_regions(ax, scenario)
    used_indices: set[int] = set()
    colors = plt.cm.viridis(np.linspace(0.08, 0.92, len(sample_times_s)))
    for target_time in sample_times_s:
        idx = int(np.argmin(np.abs(time - target_time)))
        if idx in used_indices:
            continue
        used_indices.add(idx)
        color = colors[len(used_indices) - 1]
        ax.plot(
            radius_mm,
            profiles[idx],
            color=color,
            lw=2.0,
            label=f"t = {time[idx]:.2g} s",
        )

    ax.set_xlabel("радиус, мм")
    ax.set_ylabel("температура, K")
    ax.set_title("Радиальные профили температуры в ТВЭЛе")
    _style_axis(ax)
    ax.legend(frameon=True, fontsize=8.5)
    return ax


def plot_radial_temperature_map(result: dict[str, np.ndarray], ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.5))

    scenario = result["scenario"]
    radius_mm = result["r_m"] * 1e3
    time = result["time_s"]
    profiles = result["temperature_profile_k"]
    if scenario.steam_layer is not None or scenario.annular_water_layer is not None:
        gas_inner_mm = scenario.geometry.clad_outer_radius_m * 1e3
        layer_thickness_m = (
            scenario.steam_layer.thickness_m
            if scenario.steam_layer is not None
            else scenario.annular_water_layer.thickness_m
        )
        gas_outer_mm = (scenario.geometry.clad_outer_radius_m + layer_thickness_m) * 1e3
        gas_radius_mm = np.linspace(gas_inner_mm, gas_outer_mm, 5)[1:]
        radius_mm = np.concatenate([radius_mm, gas_radius_mm])
        gas_profiles = np.repeat(
            result["water_temperature_k"][:, None],
            gas_radius_mm.size,
            axis=1,
        )
        profiles = np.hstack([profiles, gas_profiles])

    image = ax.pcolormesh(
        radius_mm,
        time,
        profiles,
        shading="nearest",
        cmap="magma",
    )
    _mark_material_regions(ax, scenario)
    contour_levels = [
        level
        for level in [1000, 1500, 2000, 2500, 3000]
        if profiles.min() < level < profiles.max()
    ]
    if contour_levels:
        ax.contour(
            radius_mm,
            time,
            profiles,
            levels=contour_levels,
            colors="white",
            linewidths=0.7,
            alpha=0.8,
        )
    ax.axhline(
        scenario.pulse.duration_s,
        color="white",
        lw=1.0,
        ls="--",
        alpha=0.85,
    )
    ax.text(
        0.02,
        scenario.pulse.duration_s,
        "конец импульса",
        color="white",
        fontsize=8,
        va="bottom",
        ha="left",
    )
    ax.set_yscale("symlog", linthresh=max(scenario.pulse.duration_s, 1e-3))
    ticks = [0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
    ticks = [tick for tick in ticks if time[0] <= tick <= time[-1]]
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{tick:g}" for tick in ticks])
    ax.set_xlabel("радиус, мм")
    ax.set_ylabel("время, с")
    ax.set_title("Температурное поле T(r, t): ТВЭЛ и газовая прослойка")
    colorbar = ax.figure.colorbar(image, ax=ax, pad=0.015)
    colorbar.set_label("температура, K")
    _style_axis(ax)
    return ax


def plot_energy_balance(result: dict[str, np.ndarray], ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.5))
    t = result["time_s"]
    scenario = result["scenario"]
    scale = max(scenario.pulse.energy_j_per_m, 1.0)
    ax.plot(
        t,
        result["pulse_energy_j_per_m"] / scale,
        color="#222222",
        lw=1.5,
        label="внесенная энергия",
    )
    ax.plot(
        t,
        result["fuel_energy_j_per_m"] / scale,
        color=LINE_COLORS["fuel_center"],
        lw=2.0,
        label="в топливе",
    )
    ax.plot(
        t,
        result["clad_energy_j_per_m"] / scale,
        color=LINE_COLORS["clad_outer"],
        lw=2.0,
        label="в оболочке",
    )
    ax.plot(
        t,
        result["water_energy_j_per_m"] / scale,
        color=LINE_COLORS["water"],
        lw=2.3,
        ls="--",
        label=(
            "в воде/паре у оболочки"
            if scenario.annular_water_layer
            else "в паровой прослойке" if scenario.steam_layer else "в воде/паре"
        ),
    )
    peak_water_percent = 100.0 * float(result["water_energy_j_per_m"].max()) / scale
    _mark_pulse_end(ax, result)
    ax.set_title("V1: куда уходит энергия импульса")
    ax.set_xlabel("время, с")
    ax.set_ylabel("доля от энергии импульса")
    ax.set_ylim(-0.03, 1.05)
    ax.text(
        0.98,
        0.12,
        f"макс. в воде/паре: {peak_water_percent:.3f}%",
        transform=ax.transAxes,
        ha="right",
        va="center",
        fontsize=8.6,
        color=LINE_COLORS["water"],
        bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.9},
    )
    _style_axis(ax)
    ax.legend(frameon=True, fontsize=8.3, loc="center right")
    return ax


def plot_water_state(result: dict[str, np.ndarray], chemistry=None, ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.5))
    scenario = result["scenario"]
    fluid_label = _fluid_label(scenario)
    t = result["time_s"]
    ax.plot(
        t,
        result["water_temperature_k"],
        color=LINE_COLORS["water"],
        lw=2.0,
        label=f"T: {fluid_label}",
    )
    ax.axhline(
        scenario.water.saturation_temperature_k,
        color="#2166ac",
        ls=":",
        lw=1.2,
        label="Tsat",
    )
    if scenario.chemistry_threshold_k <= result["water_temperature_k"].max() * 1.08:
        ax.axhline(
            scenario.chemistry_threshold_k,
            color="#8c510a",
            ls="--",
            lw=1.1,
            label="порог химии",
        )
    _mark_pulse_end(ax, result)
    ax.set_title(
        "Состояние воды у оболочки"
        if scenario.annular_water_layer
        else "Состояние газовой прослойки" if scenario.steam_layer else "Состояние воды"
    )
    ax.set_xlabel("время, с")
    ax.set_ylabel("температура, K")
    ax_quality = ax.twinx()
    ax_quality.plot(
        t,
        result["vapor_quality"],
        color="#4d9221",
        lw=1.9,
        label="паросодержание",
    )
    ax_quality.set_ylabel("паросодержание")
    ax_quality.set_ylim(-0.05, 1.08)
    if chemistry is not None:
        peak_h2 = float(chemistry["peak_hydrogen_g_per_m"])
        ax.text(
            0.98,
            0.06,
            f"макс. H2 = {peak_h2:.2g} г/м",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=8.5,
            bbox={"facecolor": "white", "edgecolor": "#c7c7c7", "alpha": 0.88},
        )
    _style_axis(ax)
    lines, labels = ax.get_legend_handles_labels()
    quality_lines, quality_labels = ax_quality.get_legend_handles_labels()
    ax.legend(lines + quality_lines, labels + quality_labels, frameon=True, fontsize=8.5)
    return ax


def plot_chemistry_temperature_margin(result: dict[str, np.ndarray], ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.5))
    scenario = result["scenario"]
    time_s = result["time_s"]
    ax.plot(
        time_s,
        result["water_temperature_k"],
        color=LINE_COLORS["water"],
        lw=2.0,
        label=f"T: {_fluid_label(scenario)}",
    )
    ax.plot(
        time_s,
        result["clad_outer_k"],
        color=LINE_COLORS["clad_outer"],
        lw=1.9,
        label="T наружной оболочки",
    )
    ax.plot(
        time_s,
        result["fuel_center_k"],
        color=LINE_COLORS["fuel_center"],
        lw=1.6,
        alpha=0.85,
        label="T центра топлива",
    )
    clad_limit_k = scenario.clad.limit_temperature_k
    ax.axhline(
        clad_limit_k,
        color="#1b7837",
        ls="--",
        lw=1.1,
        label=f"предел оболочки {scenario.clad.name}",
    )
    if clad_limit_k < scenario.clad.melting_temperature_k:
        ax.axhline(
            scenario.clad.melting_temperature_k,
            color="#1b7837",
            ls=":",
            lw=1.0,
            alpha=0.85,
            label=f"плавление {scenario.clad.name}",
        )
    ax.axhline(
        scenario.fuel.melting_temperature_k,
        color="#7a1f1f",
        ls="--",
        lw=1.1,
        label=f"плавление {scenario.fuel.name}",
    )
    ax.axhline(
        scenario.chemistry_threshold_k,
        color="#542788",
        ls="-.",
        lw=1.3,
        label="порог термолиза",
    )
    _mark_pulse_end(ax, result)
    ax.set_title("Достижимость химического температурного окна")
    ax.set_xlabel("время, с")
    ax.set_ylabel("температура, K")
    ax.set_ylim(
        scenario.initial_solid_temperature_k - 40.0,
        max(scenario.chemistry_threshold_k, result["fuel_center_k"].max()) * 1.05,
    )
    _style_axis(ax)
    ax.legend(frameon=True, fontsize=8.2, ncol=2)
    return ax
