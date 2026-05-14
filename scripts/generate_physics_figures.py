from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patheffects as pe
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, PathPatch, Rectangle
from matplotlib.path import Path as MplPath


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"


plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "mathtext.fontset": "dejavusans",
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.dpi": 180,
    }
)


def save(fig: plt.Figure, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / f"{name}.png", bbox_inches="tight", dpi=220)
    plt.close(fig)


def flow_patch(
    x0: float,
    y0a: float,
    y0b: float,
    x1: float,
    y1a: float,
    y1b: float,
    color: str,
    alpha: float = 0.82,
) -> PathPatch:
    xm = (x0 + x1) / 2.0
    verts = [
        (x0, y0a),
        (xm, y0a),
        (xm, y1a),
        (x1, y1a),
        (x1, y1b),
        (xm, y1b),
        (xm, y0b),
        (x0, y0b),
        (x0, y0a),
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.LINETO,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CLOSEPOLY,
    ]
    return PathPatch(MplPath(verts, codes), facecolor=color, edgecolor="none", alpha=alpha)


def add_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    w: float,
    h: float,
    text: str,
    fc: str,
    ec: str = "#263238",
    fontsize: int = 12,
    weight: str = "bold",
    color: str = "black",
    radius: float = 0.025,
) -> FancyBboxPatch:
    box = FancyBboxPatch(
        xy,
        w,
        h,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        facecolor=fc,
        edgecolor=ec,
        linewidth=1.4,
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + w / 2,
        xy[1] + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        weight=weight,
        color=color,
        linespacing=1.15,
    )
    return box


def add_arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = "#37474f",
    lw: float = 2.0,
    mutation_scale: float = 15.0,
    style: str = "-|>",
    connectionstyle: str = "arc3,rad=0",
    alpha: float = 1.0,
    linestyle: str = "-",
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=mutation_scale,
            linewidth=lw,
            color=color,
            alpha=alpha,
            linestyle=linestyle,
            connectionstyle=connectionstyle,
        )
    )


def make_fig0_fuel_memory_concept() -> None:
    fig, axes = plt.subplots(
        1,
        3,
        figsize=(13.8, 5.8),
        gridspec_kw={"width_ratios": [1.08, 1.05, 1.0], "wspace": 0.27},
    )
    ax0, ax1, ax2 = axes
    fig.suptitle(
        "Что такое память твэла: прошлое энерговыделение остаётся в температурном следе",
        fontsize=17,
        weight="bold",
        y=0.985,
    )

    t = np.linspace(0, 120, 900)
    t_now = 92.0
    events = np.array([18.0, 41.0, 66.0, 82.0])
    amplitudes = np.array([0.75, 1.05, 0.62, 0.45])
    widths = np.array([4.0, 5.5, 4.5, 3.0])
    colors = ["#8e2d2d", "#c45a32", "#d69a35", "#4d90c6"]

    P = np.zeros_like(t)
    for s, a, w in zip(events, amplitudes, widths):
        P += a * np.exp(-0.5 * ((t - s) / w) ** 2)
    P += 0.04

    ax0.plot(t, P, color="#263238", lw=2.4)
    ax0.fill_between(t, 0, P, where=t <= t_now, color="#90caf9", alpha=0.22)
    ax0.axvline(t_now, color="#111111", lw=1.7, ls="--")
    for s, a, c in zip(events, amplitudes, colors):
        ax0.axvline(s, color=c, lw=1.4, alpha=0.85)
        ax0.text(s, 1.23, "$s_i$", ha="center", va="bottom", fontsize=10, color=c)
    ax0.text(t_now + 1.5, 1.02, "текущий\nмомент $t$", ha="left", va="center", fontsize=10.5)
    ax0.text(45, 0.25, "твэл видит\nвсю прошлую\nисторию $P(s)$", ha="center", fontsize=11, color="#0d47a1")
    ax0.set_title("(а) История мощности", pad=9)
    ax0.set_xlabel("время $s$, мс")
    ax0.set_ylabel("$P(s)$, отн. ед.")
    ax0.set_xlim(0, 120)
    ax0.set_ylim(0, 1.35)
    ax0.grid(True, alpha=0.25)

    tau_f = 30.0
    traces = []
    for s, a in zip(events, amplitudes):
        tr = np.where(t >= s, a * np.exp(-(t - s) / tau_f), 0.0)
        traces.append(tr)
    traces = np.array(traces)
    total_trace = traces.sum(axis=0)

    for tr, c, s in zip(traces, colors, events):
        ax1.plot(t, tr, color=c, lw=1.9, alpha=0.85)
        ax1.fill_between(t, 0, tr, color=c, alpha=0.08)
        idx = np.argmin(np.abs(t - t_now))
        ax1.scatter([t_now], [tr[idx]], color=c, s=28, zorder=5)
    ax1.plot(t, total_trace, color="#111111", lw=2.6, label="суммарный след")
    ax1.axvline(t_now, color="#111111", lw=1.7, ls="--")
    ax1.scatter([t_now], [np.interp(t_now, t, total_trace)], color="#111111", s=40, zorder=6)
    ax1.text(
        14,
        1.55,
        "прошлые события\nне исчезают сразу:\nони дают остаточную\n$\\Delta T_f(r,t)$",
        ha="left",
        va="top",
        fontsize=10.8,
        bbox=dict(boxstyle="round,pad=0.28", fc="white", ec="#6d4c41", alpha=0.95),
    )
    ax1.text(
        t_now + 2,
        np.interp(t_now, t, total_trace),
        "накопленная\nпамять",
        ha="left",
        va="center",
        fontsize=10.5,
        weight="bold",
    )
    ax1.set_title("(б) Температурный след топлива", pad=9)
    ax1.set_xlabel("время, мс")
    ax1.set_ylabel("остаточный вклад в $T_f$")
    ax1.set_xlim(0, 120)
    ax1.set_ylim(0, 1.75)
    ax1.grid(True, alpha=0.25)

    lag = np.linspace(0, 110, 700)
    KD = np.exp(-lag / 4.0)
    H = (lag / 55.0) ** 1.7 * np.exp(1.7 * (1 - lag / 55.0))
    H[lag == 0] = 0.0
    H /= H.max()
    ax2.plot(lag, KD, color="#2e7d32", lw=2.6, label="$K_D(\\tau)$")
    ax2.plot(lag, H, color="#1565c0", lw=2.6, ls="--", label="$H_{fw}(\\tau)$")
    ax2.fill_between(lag, 0, KD, color="#2e7d32", alpha=0.12)
    ax2.fill_between(lag, 0, H, color="#1565c0", alpha=0.13)
    ax2.text(13, 0.72, "быстрая\nреактивностная\nпамять", color="#1b5e20", fontsize=10.5)
    ax2.text(61, 0.77, "медленная\nтепловая\nпамять", color="#0d47a1", fontsize=10.5)
    ax2.text(
        0.50,
        -0.26,
        "$I_D(t)=\\int_0^t K_D(t-s)P(s)ds$\n$Q_{fw}(t)=\\int_0^t H_{fw}(t-s)P(s)ds$",
        transform=ax2.transAxes,
        ha="center",
        va="top",
        fontsize=11.2,
        bbox=dict(boxstyle="round,pad=0.35", fc="#f7f7f7", ec="#555555", alpha=0.98),
    )
    ax2.set_title("(в) Память как свёртка", pad=9)
    ax2.set_xlabel("возраст следа $\\tau=t-s$, мс")
    ax2.set_ylabel("вес прошлого события")
    ax2.set_xlim(0, 110)
    ax2.set_ylim(0, 1.15)
    ax2.grid(True, alpha=0.25)
    ax2.legend(loc="upper right", framealpha=0.96)

    fig.subplots_adjust(bottom=0.25)
    save(fig, "fig0_fuel_memory_concept")


def make_fig8_energy_partition() -> None:
    fig, ax = plt.subplots(figsize=(13.6, 7.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.965,
        "Куда уходит энергия деления: что нагревает топливо, что доходит до воды, что теряется",
        ha="center",
        va="top",
        fontsize=18,
        weight="bold",
    )

    source_x0, source_x1 = 0.07, 0.17
    target_x0, target_x1 = 0.68, 0.90

    add_box(
        ax,
        (source_x0, 0.34),
        source_x1 - source_x0,
        0.30,
        "деление\n$^{235}$U\n$\\sim 200$ МэВ",
        "#45515b",
        ec="#20262b",
        color="white",
        fontsize=13,
    )

    channels = [
        ("Осколки деления", "168 МэВ", 0.56, 0.36, "#b63a32", "локально,\nмкм-пробег"),
        ("γ, β и γ-продукты", "20 МэВ", 0.40, 0.07, "#d9823b", "распределённо\nи частично с задержкой"),
        ("Нейтроны деления", "5 МэВ", 0.30, 0.035, "#5aa6d8", "перенос и\nзамедление"),
        ("Антинейтрино", "10 МэВ", 0.215, 0.045, "#b5b5b5", "покидают систему"),
    ]

    target_segments = {
        "fuel_main": (0.74, 0.36),
        "fuel_dist": (0.53, 0.075),
        "water": (0.335, 0.04),
        "loss": (0.17, 0.055),
    }

    for label, value, yc, h, color, note in channels:
        ax.add_patch(
            Rectangle(
                (source_x0 - 0.018, yc - h / 2),
                0.018,
                h,
                facecolor=color,
                edgecolor="none",
                alpha=0.95,
            )
        )
        ax.text(
            source_x0 - 0.03,
            yc,
            f"{label}\n{value}",
            ha="right",
            va="center",
            fontsize=10.5,
            linespacing=1.15,
        )
        ax.text(
            0.49,
            yc + (0.04 if label == "Осколки деления" else 0.0),
            note,
            ha="center",
            va="center",
            fontsize=10.5,
            color="#2f2f2f",
            style="italic",
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="none", alpha=0.85),
        )

    flow_specs = [
        (0.56, 0.36, *target_segments["fuel_main"], "#b63a32"),
        (0.40, 0.07, *target_segments["fuel_dist"], "#d9823b"),
        (0.30, 0.035, *target_segments["water"], "#5aa6d8"),
        (0.215, 0.045, *target_segments["loss"], "#b5b5b5"),
    ]
    for yc0, h0, yc1, h1, color in flow_specs:
        ax.add_patch(
            flow_patch(
                source_x1,
                yc0 - h0 / 2,
                yc0 + h0 / 2,
                target_x0,
                yc1 - h1 / 2,
                yc1 + h1 / 2,
                color,
            )
        )

    add_box(
        ax,
        (target_x0, 0.49),
        target_x1 - target_x0,
        0.41,
        "НАГРЕВ ТВЭЛА\n$\\approx 188$ МэВ\nсоздаёт $T_f(r,t)$\nи доплеровскую память",
        "#f2d6d3",
        ec="#8a302a",
        fontsize=12,
        color="#6b1c1c",
    )
    add_box(
        ax,
        (target_x0, 0.285),
        target_x1 - target_x0,
        0.10,
        "НАГРЕВ ВОДЫ\n$\\approx 5$ МэВ\nпосле переноса",
        "#d7eaf7",
        ec="#1d6fa7",
        fontsize=12,
        color="#0d416c",
    )
    add_box(
        ax,
        (target_x0, 0.095),
        target_x1 - target_x0,
        0.11,
        "ПОТЕРЯ\n$\\approx 10$ МэВ\nне депонируется",
        "#eeeeee",
        ec="#6e6e6e",
        fontsize=12,
        color="#555555",
    )

    ax.text(
        0.935,
        0.78,
        "$K_D(t)$\nбыстрый\nреактивностный\nвыход",
        ha="left",
        va="center",
        fontsize=12,
        color="#6b1c1c",
        weight="bold",
    )
    ax.text(
        0.935,
        0.335,
        "$H_{fw}(t)$\nзадержанный\nтепловой\nвыход",
        ha="left",
        va="center",
        fontsize=12,
        color="#0d416c",
        weight="bold",
    )

    ax.text(
        0.50,
        0.055,
        "Числа даны как порядок вклада одного акта деления; в модели важна не только сумма энергии, но и место и время её депонирования.",
        ha="center",
        va="center",
        fontsize=10.5,
        color="#333333",
    )
    save(fig, "fig8_energy_partition")


def make_fig9_thermal_propagation() -> None:
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(13.6, 6.1),
        gridspec_kw={"width_ratios": [1.08, 1.0], "wspace": 0.22},
    )
    ax0, ax1 = axes
    fig.suptitle(
        "Тепловая диффузия в твэле: почему вода видит сглаженный хвост импульса",
        fontsize=18,
        y=0.98,
    )

    t = np.logspace(-2, 2.5, 260)
    x = np.linspace(0, 0.36, 180)
    T, X = np.meshgrid(t, x)
    alpha_f = 1.0e-3
    thermal_depth = np.sqrt(alpha_f * T)
    Z = np.exp(-((X / (2.0 * thermal_depth + 1.0e-6)) ** 2))
    Z *= np.exp(-T / 520.0)
    Z = np.clip(Z, 0, 1)

    mesh = ax0.pcolormesh(t, x, Z, shading="auto", cmap="inferno", vmin=0, vmax=1)
    ax0.set_xscale("log")
    ax0.set_xlim(1e-2, 3e2)
    ax0.set_ylim(0, 0.36)
    ax0.set_title("(а) Тепловой след: $\\ell_T(t)=\\sqrt{\\alpha_f t}$", pad=10)
    ax0.set_xlabel("время после импульса $t$, мс")
    ax0.set_ylabel("эффективное расстояние от зоны нагрева, мм")

    layers = [
        (0.00, 0.16, "UO$_2$", "#f8e6e6"),
        (0.16, 0.20, "gap", "#fff5b8"),
        (0.20, 0.26, "Zr", "#d7dce0"),
        (0.26, 0.36, "H$_2$O", "#d7ebfb"),
    ]
    for y0, y1, label, color in layers:
        ax0.axhspan(y0, y1, color=color, alpha=0.18, lw=0)
        ax0.text(
            0.016,
            (y0 + y1) / 2,
            label,
            ha="left",
            va="center",
            fontsize=11,
            color="#263238",
            path_effects=[pe.withStroke(linewidth=3, foreground="white")],
        )
        if y1 < 0.36:
            ax0.axhline(y1, color="#546e7a", lw=0.9, alpha=0.75)

    tau_k = 2.0
    tau_h = 67.0
    ax0.axvline(tau_k, color="#2ca02c", lw=1.8, ls="--")
    ax0.axvline(tau_h, color="#1f77b4", lw=1.8, ls="--")
    ax0.plot(t, np.sqrt(alpha_f * t), color="#24c6dc", lw=2.2, ls=":")
    ax0.text(tau_k * 1.08, 0.325, "$\\tau_K\\sim2$ мс", color="#1b7f27", fontsize=11, weight="bold")
    ax0.text(tau_h * 1.05, 0.303, "$\\tau_H\\sim67$ мс", color="#0e4a78", fontsize=11, weight="bold")
    ax0.text(
        18,
        0.273,
        "$\\ell_T(\\tau_H)\\sim L_{eff}$",
        color="#073763",
        fontsize=11,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#1f77b4", alpha=0.9),
    )
    cb = fig.colorbar(mesh, ax=ax0, fraction=0.046, pad=0.02)
    cb.set_label("$\\Delta T(x,t)/\\Delta T_{max}$")

    tt = np.linspace(0.0, 220.0, 900)
    KD = np.exp(-tt / 3.0)
    KD /= KD.max()
    H = (tt / tau_h) ** 1.75 * np.exp(1.75 * (1 - tt / tau_h))
    H[tt == 0] = 0
    H /= H.max()

    ax1.plot(tt, KD, color="#2ca02c", lw=2.7, label="$K_D(t)$ — доплеровский канал")
    ax1.fill_between(tt, KD, color="#2ca02c", alpha=0.12)
    ax1.plot(tt, H, color="#1f77b4", lw=2.7, ls="--", label="$H_{fw}(t)$ — канал в воду")
    ax1.fill_between(tt, H, color="#1f77b4", alpha=0.16)
    ax1.axvline(tau_k, color="#2ca02c", lw=1.8, ls=":")
    ax1.axvline(tau_h, color="#1f77b4", lw=1.8, ls=":")
    ax1.text(4.5, 0.86, "самогашение\nмощности", color="#17651e", fontsize=11)
    ax1.text(118, 0.46, "задержанный\nнагрев воды", color="#073763", fontsize=11, ha="center")
    ax1.text(8, 1.03, "$\\tau_K\\ll\\tau_H$", fontsize=12, weight="bold")
    ax1.set_title("(б) Два выхода одного температурного следа", pad=10)
    ax1.set_xlabel("время от начала импульса $t$, мс")
    ax1.set_ylabel("нормированная функция отклика")
    ax1.set_xlim(0, 220)
    ax1.set_ylim(0, 1.1)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper right", frameon=True, framealpha=0.95)

    save(fig, "fig9_thermal_propagation")


def make_fig10_causal_structure() -> None:
    fig, ax = plt.subplots(figsize=(13.6, 7.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(
        0.5,
        0.965,
        "Структура системы: от нейтронного импульса к самогашению и теплу в воде",
        ha="center",
        va="top",
        fontsize=18,
        weight="bold",
    )

    common = dict(w=0.17, h=0.11, fontsize=11)
    boxes = {
        "p": (0.055, 0.57, "Мощность\n$P(t)$\nнейтронный\nимпульс", "#e8f1ff", "#1f5e9f"),
        "q": (0.285, 0.57, "Деления в\nUO$_2$\n$q'''(r,t)$", "#fff2cc", "#a96800"),
        "tf": (0.515, 0.57, "Температурный\nслед топлива\n$T_f(r,t)$", "#fde3dc", "#a33a24"),
        "doppler": (0.735, 0.74, "Доплеровское\nуширение\n$\\sigma_a(E,T_f)$", "#e5f4df", "#2e7d32"),
        "rho": (0.735, 0.57, "Отрицательная\nреактивность\n$-\\rho_D(t)$", "#dff2e1", "#2e7d32"),
        "heat": (0.735, 0.36, "Теплопроводность\nтопливо → gap → Zr", "#f4e6ff", "#6a3d9a"),
        "water": (0.735, 0.18, "Вода\n$Q_{fw}(t)$,\n$T_w,p,x_w$", "#dceffb", "#1565c0"),
    }
    for key, (x, y, text, fc, ec) in boxes.items():
        add_box(ax, (x, y), common["w"], common["h"], text, fc, ec=ec, fontsize=common["fontsize"])

    add_arrow(ax, (0.225, 0.625), (0.285, 0.625), color="#455a64")
    add_arrow(ax, (0.455, 0.625), (0.515, 0.625), color="#455a64")
    add_arrow(ax, (0.685, 0.655), (0.735, 0.78), color="#2e7d32", connectionstyle="arc3,rad=0.10")
    add_arrow(ax, (0.82, 0.74), (0.82, 0.68), color="#2e7d32")
    add_arrow(ax, (0.735, 0.61), (0.225, 0.61), color="#2e7d32", connectionstyle="arc3,rad=0.34")
    add_arrow(ax, (0.685, 0.58), (0.735, 0.415), color="#6a3d9a", connectionstyle="arc3,rad=-0.12")
    add_arrow(ax, (0.82, 0.36), (0.82, 0.29), color="#1565c0")
    add_arrow(
        ax,
        (0.735, 0.225),
        (0.225, 0.585),
        color="#1565c0",
        lw=1.6,
        alpha=0.55,
        linestyle="--",
        connectionstyle="arc3,rad=-0.42",
    )

    ax.text(
        0.56,
        0.82,
        "быстрый объёмный выход\n$K_D(t)$, миллисекунды",
        ha="center",
        va="center",
        fontsize=11,
        color="#1b5e20",
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#2e7d32", alpha=0.96),
    )
    ax.text(
        0.56,
        0.32,
        "медленный граничный выход\n$H_{fw}(t)$, десятки миллисекунд",
        ha="center",
        va="center",
        fontsize=11,
        color="#0d47a1",
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#1565c0", alpha=0.96),
    )
    ax.text(
        0.395,
        0.725,
        "энергия сначала\nдепонируется в топливе",
        ha="center",
        va="center",
        fontsize=10.5,
        color="#6d4c00",
    )
    ax.text(
        0.39,
        0.145,
        "Один температурный след топлива имеет два функционала:\nбыстрый реактивностный и задержанный тепловой.",
        ha="center",
        va="center",
        fontsize=11,
        color="#333333",
    )

    timeline_y = 0.045
    ax.plot([0.10, 0.90], [timeline_y, timeline_y], color="#37474f", lw=1.6)
    marks = [
        (0.18, "ядерное\nсобытие", "#a96800"),
        (0.47, "$\\tau_K$", "#2e7d32"),
        (0.82, "$\\tau_H$", "#1565c0"),
    ]
    for x, label, color in marks:
        ax.plot([x, x], [timeline_y - 0.012, timeline_y + 0.012], color=color, lw=2)
        ax.text(x, timeline_y - 0.025, label, ha="center", va="top", fontsize=10.5, color=color)
    ax.text(0.5, timeline_y + 0.025, "временная иерархия", ha="center", va="bottom", fontsize=10.5)

    save(fig, "fig10_causal_structure")


def main() -> None:
    make_fig0_fuel_memory_concept()
    make_fig8_energy_partition()
    make_fig9_thermal_propagation()
    make_fig10_causal_structure()


if __name__ == "__main__":
    main()
