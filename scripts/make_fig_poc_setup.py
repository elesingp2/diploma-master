#!/usr/bin/env python3
"""Generate the proof-of-concept test-stand schematic for the thesis."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "mathtext.fontset": "dejavusans",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "figure.dpi": 180,
    }
)


def add_box(ax, xy, width, height, text, fc, ec="#334155", fontsize=9.8):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.018,rounding_size=0.018",
        facecolor=fc,
        edgecolor=ec,
        linewidth=1.1,
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        linespacing=1.12,
    )
    return box


def arrow(ax, start, end, color="#475569", lw=1.7, ms=12, rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=ms,
            linewidth=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def make_figure() -> None:
    fig, ax = plt.subplots(figsize=(11.4, 5.6))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(
        0.5,
        0.965,
        "Нереакторный стенд для проверки принципа импульсного нагрева",
        ha="center",
        va="top",
        fontsize=14.2,
        weight="bold",
    )

    add_box(ax, (0.04, 0.46), 0.14, 0.13, "вода / пар\nподготовка среды", "#dff2fb")
    add_box(ax, (0.23, 0.46), 0.13, 0.13, "насос\nи давление", "#e5ebf0")
    add_box(ax, (0.41, 0.46), 0.12, 0.13, "подогрев\nсреды", "#fff1c7")
    add_box(ax, (0.80, 0.46), 0.14, 0.13, "охладитель\nи конденсация", "#dff2fb")
    add_box(ax, (0.78, 0.19), 0.17, 0.11, "газовая проба\nи анализ $H_2$", "#eef7ee")
    add_box(ax, (0.04, 0.18), 0.16, 0.11, "сброс давления\nи защита", "#f3f4f6")

    # Main protective chamber and test section.
    chamber = FancyBboxPatch(
        (0.56, 0.34),
        0.18,
        0.36,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        facecolor="#f8fafc",
        edgecolor="#111827",
        linewidth=1.25,
    )
    ax.add_patch(chamber)
    ax.text(0.65, 0.675, "защитный кожух", ha="center", va="center", fontsize=9.5)
    ax.add_patch(Rectangle((0.635, 0.39), 0.03, 0.22, facecolor="#c2410c", edgecolor="#7c2d12", lw=1.0))
    ax.add_patch(Rectangle((0.625, 0.385), 0.05, 0.23, fill=False, edgecolor="#334155", lw=1.0))
    ax.text(
        0.65,
        0.355,
        "модельный стержень\nв воде или паре",
        ha="center",
        va="top",
        fontsize=9.0,
    )

    # Main loop arrows.
    arrow(ax, (0.18, 0.525), (0.23, 0.525))
    arrow(ax, (0.36, 0.525), (0.41, 0.525))
    arrow(ax, (0.53, 0.525), (0.56, 0.525))
    arrow(ax, (0.74, 0.525), (0.80, 0.525))
    arrow(ax, (0.87, 0.46), (0.87, 0.28), rad=-0.1)
    arrow(ax, (0.80, 0.235), (0.20, 0.235), rad=-0.04)
    arrow(ax, (0.12, 0.29), (0.12, 0.46), rad=-0.05)

    # Pulse power and diagnostics.
    add_box(ax, (0.34, 0.76), 0.20, 0.12, "источник\nимпульсного тока", "#fbe5d6")
    add_box(ax, (0.68, 0.77), 0.22, 0.11, "пирометрия,\nтермопары, давление", "#e8eefc")
    add_box(ax, (0.42, 0.08), 0.20, 0.10, "сбор данных\nи синхронизация", "#eef2ff")

    arrow(ax, (0.54, 0.81), (0.635, 0.61), color="#b91c1c", lw=2.0, ms=13)
    arrow(ax, (0.68, 0.78), (0.665, 0.60), color="#1d4ed8", lw=1.8, ms=12)
    arrow(ax, (0.71, 0.77), (0.57, 0.18), color="#4f46e5", lw=1.5, ms=11, rad=0.16)
    arrow(ax, (0.665, 0.39), (0.78, 0.245), color="#15803d", lw=1.7, ms=12)
    arrow(ax, (0.76, 0.77), (0.56, 0.18), color="#4f46e5", lw=1.5, ms=11, rad=-0.16)

    ax.text(
        0.50,
        0.025,
        "Основные измеряемые выходы: $T_s^{\\max}$, запас материала до предела, "
        "доля энергии, прошедшая в воду или пар.",
        ha="center",
        va="bottom",
        fontsize=9.6,
        color="#374151",
    )

    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / "fig16_poc_setup.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / "fig16_poc_setup.png", bbox_inches="tight", dpi=220)
    plt.close(fig)
    print("Wrote figures/fig16_poc_setup.pdf")


if __name__ == "__main__":
    make_figure()
