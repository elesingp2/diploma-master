#!/usr/bin/env python3
"""Generate the active fuel-pin anatomy figure for the thesis."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "mathtext.fontset": "dejavusans",
        "figure.dpi": 180,
    }
)


def add_box(ax, xy, width, height, text, fc, ec="#374151", fontsize=10.5):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        facecolor=fc,
        edgecolor=ec,
        linewidth=1.2,
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        linespacing=1.15,
    )
    return box


def arrow(ax, start, end, color="#7a1f1f", lw=2.0, ms=14, rad=0.0):
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
    fig, (ax0, ax1) = plt.subplots(
        1,
        2,
        figsize=(11.2, 4.45),
        gridspec_kw={"width_ratios": [1.0, 1.12], "wspace": 0.18},
        constrained_layout=True,
    )

    for ax in (ax0, ax1):
        ax.set_axis_off()

    ax0.set_xlim(-1.25, 1.35)
    ax0.set_ylim(-1.18, 1.20)
    ax0.set_aspect("equal")

    layers = [
        (1.02, "#cfe7f7", "#5b91b5"),
        (0.79, "#aab5be", "#3f4d58"),
        (0.68, "#f5f2df", "#8b7d38"),
        (0.64, "#f0a23a", "#8c4d13"),
    ]
    for radius, fc, ec in layers:
        ax0.add_patch(Circle((0, 0), radius, facecolor=fc, edgecolor=ec, lw=1.4))

    ax0.add_patch(Circle((0, 0), 0.24, facecolor="#e66b2e", edgecolor="none", alpha=0.38))
    ax0.text(0, 0.07, "топливо\n$UO_2$", ha="center", va="center", fontsize=11, weight="bold")
    ax0.text(0, -0.22, "$q'''(t)$\nтолько в топливе", ha="center", va="center", fontsize=9.8)

    for angle in [20, 75, 135, 210, 290]:
        x0 = 0.34 * np.cos(np.deg2rad(angle))
        y0 = 0.34 * np.sin(np.deg2rad(angle))
        x1 = 0.93 * np.cos(np.deg2rad(angle))
        y1 = 0.93 * np.sin(np.deg2rad(angle))
        arrow(ax0, (x0, y0), (x1, y1), color="#d94801", lw=1.8, ms=12)

    ax0.annotate(
        "газовый зазор\n$h_g$",
        xy=(0.66, 0.10),
        xytext=(-1.18, 0.72),
        arrowprops={"arrowstyle": "->", "lw": 1.0, "color": "#263238"},
        ha="left",
        va="center",
        fontsize=9.6,
    )
    ax0.annotate(
        "оболочка\n$T_c(t)$",
        xy=(0.83, -0.06),
        xytext=(-1.15, -0.55),
        arrowprops={"arrowstyle": "->", "lw": 1.0, "color": "#263238"},
        ha="left",
        va="center",
        fontsize=9.6,
    )
    ax0.annotate(
        "вода / пар\n$T_s(t)$",
        xy=(1.0, -0.30),
        xytext=(0.50, -1.03),
        arrowprops={"arrowstyle": "->", "lw": 1.0, "color": "#263238"},
        ha="left",
        va="center",
        fontsize=9.6,
    )
    ax0.text(0, 1.12, "(а) Контрольный объем", ha="center", va="top", fontsize=12, weight="bold")
    ax0.text(0.0, 0.96, "$q''_{cw}$", ha="center", va="center", fontsize=11, color="#c53a00", weight="bold")

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.text(
        0.50,
        0.95,
        "(б) Расчетная причинная цепочка",
        ha="center",
        va="top",
        fontsize=12,
        weight="bold",
    )

    boxes = [
        (0.05, 0.66, 0.17, 0.16, "импульс\n$E_{\\mathrm{вв}}$", "#eef2ff"),
        (0.29, 0.66, 0.18, 0.16, "объемный\nисточник\n$q'''(t)$", "#fff3cf"),
        (0.55, 0.66, 0.18, 0.16, "температура\nтоплива\n$T_f(r,t)$", "#fde6d2"),
        (0.78, 0.66, 0.17, 0.16, "тепловой\nпоток\n$q''_g$", "#f8fafc"),
        (0.29, 0.34, 0.20, 0.16, "оболочка\n$T_c(t)$", "#e5ebf0"),
        (0.57, 0.34, 0.20, 0.16, "поток к пару\n$q''_{cw}$", "#f8fafc"),
        (0.80, 0.34, 0.15, 0.16, "пар\n$T_s(t)$", "#dff2fb"),
        (0.57, 0.10, 0.38, 0.14, "критерий:\n$T_s$, запас материалов, $m_{H_2}^{\\max}$", "#eef7ee"),
    ]
    for box in boxes:
        add_box(ax1, box[:2], box[2], box[3], box[4], box[5], fontsize=9.7)

    arrow(ax1, (0.22, 0.74), (0.29, 0.74), color="#475569", lw=1.7, ms=12)
    arrow(ax1, (0.47, 0.74), (0.55, 0.74), color="#475569", lw=1.7, ms=12)
    arrow(ax1, (0.73, 0.74), (0.78, 0.74), color="#475569", lw=1.7, ms=12)
    arrow(ax1, (0.86, 0.66), (0.39, 0.50), color="#475569", lw=1.7, ms=12, rad=-0.25)
    arrow(ax1, (0.49, 0.42), (0.57, 0.42), color="#475569", lw=1.7, ms=12)
    arrow(ax1, (0.77, 0.42), (0.80, 0.42), color="#475569", lw=1.7, ms=12)
    arrow(ax1, (0.875, 0.34), (0.76, 0.24), color="#1b7837", lw=1.8, ms=12)

    ax1.text(
        0.07,
        0.18,
        "Важно: высокая $T_f$ не засчитывается\nкак результат, пока тепло не дошло\nдо паровой области у оболочки.",
        ha="left",
        va="center",
        fontsize=9.7,
        color="#334155",
    )

    fig.suptitle(
        "Анатомия твэла: где выделяется энергия и куда идет тепло",
        fontsize=14.2,
        y=1.02,
    )
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / "fig7_fuel_pin_anatomy.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / "fig7_fuel_pin_anatomy.png", bbox_inches="tight", dpi=220)
    plt.close(fig)
    print("Wrote figures/fig7_fuel_pin_anatomy.pdf")


if __name__ == "__main__":
    make_figure()
