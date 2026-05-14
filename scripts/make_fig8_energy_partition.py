#!/usr/bin/env python3
"""Regenerate fig8_energy_partition with high-contrast labels."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"


def ribbon(ax, x0, x1, y0, y1, width0, width1, color, alpha=0.86):
    """Draw a smooth constant-or-changing-width ribbon between two points."""
    dx = x1 - x0
    c0 = x0 + 0.44 * dx
    c1 = x0 + 0.56 * dx
    verts = [
        (x0, y0 + width0 / 2),
        (c0, y0 + width0 / 2),
        (c1, y1 + width1 / 2),
        (x1, y1 + width1 / 2),
        (x1, y1 - width1 / 2),
        (c1, y1 - width1 / 2),
        (c0, y0 - width0 / 2),
        (x0, y0 - width0 / 2),
        (x0, y0 + width0 / 2),
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
    ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color, edgecolor="none", alpha=alpha))


def label(ax, x, y, text, size=12, weight="normal", color="#171717", ha="center"):
    ax.text(
        x,
        y,
        text,
        ha=ha,
        va="center",
        fontsize=size,
        fontweight=weight,
        color=color,
        linespacing=1.15,
        bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor="#d0d5dd", alpha=0.94),
    )


def plain(ax, x, y, text, size=12, weight="normal", color="#171717", ha="center", va="center"):
    ax.text(
        x,
        y,
        text,
        ha=ha,
        va=va,
        fontsize=size,
        fontweight=weight,
        color=color,
        linespacing=1.15,
    )


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, ax = plt.subplots(figsize=(15.2, 6.8))
    fig.patch.set_facecolor("#f7f8fa")
    ax.set_facecolor("#f7f8fa")
    ax.set_xlim(0, 13.2)
    ax.set_ylim(0, 1)
    ax.axis("off")

    plain(
        ax,
        6,
        0.965,
        "Куда уходит энергия одного акта деления (~200 МэВ)",
        size=18,
        weight="bold",
    )
    plain(
        ax,
        6,
        0.925,
        "что нагревается, что излучается и что покидает систему",
        size=12,
        color="#475467",
    )

    # Source event.
    ax.add_patch(Rectangle((1.05, 0.22), 1.05, 0.56, facecolor="#3f4a54", edgecolor="#111827", linewidth=1.0))
    plain(ax, 1.575, 0.54, "Деление\n$^{235}$U", size=13, weight="bold", color="#ffffff")
    plain(ax, 1.575, 0.42, "~200 МэВ", size=13, weight="bold", color="#ffffff")

    # Main ribbons.
    ribbon(ax, 2.10, 7.10, 0.66, 0.73, 0.36, 0.30, "#b8332f", 0.9)
    ribbon(ax, 2.10, 7.10, 0.47, 0.49, 0.10, 0.08, "#d36f28", 0.86)
    ribbon(ax, 2.10, 7.10, 0.34, 0.34, 0.12, 0.08, "#d49a63", 0.9)
    ribbon(ax, 2.10, 7.10, 0.22, 0.22, 0.055, 0.045, "#76b7e5", 0.88)
    ribbon(ax, 2.10, 7.10, 0.115, 0.095, 0.065, 0.055, "#a7a9ac", 0.9)

    # Intermediate receivers.
    ax.add_patch(Rectangle((7.10, 0.58), 1.85, 0.28, facecolor="#c7433b", edgecolor="#4b1d1a", linewidth=0.9))
    ax.add_patch(Rectangle((7.10, 0.43), 1.85, 0.09, facecolor="#dd8a48", edgecolor="#6f3d16", linewidth=0.9))
    ax.add_patch(Rectangle((7.10, 0.305), 1.85, 0.08, facecolor="#d9a06a", edgecolor="#6e4520", linewidth=0.9))
    ax.add_patch(Rectangle((7.10, 0.20), 1.85, 0.045, facecolor="#80bee8", edgecolor="#205b82", linewidth=0.9))
    ax.add_patch(Rectangle((7.10, 0.07), 1.85, 0.055, facecolor="#b9bbbd", edgecolor="#595b5e", linewidth=0.9))

    plain(ax, 8.025, 0.72, "Топливо UO$_2$", size=12.5, weight="bold")
    plain(ax, 8.025, 0.475, "Топливо + оболочка", size=11.0, weight="bold")
    plain(ax, 8.025, 0.345, "Топливо + конструкции", size=11.0, weight="bold")
    plain(ax, 8.025, 0.222, "Замедлитель / вода", size=10.0, weight="bold")
    plain(ax, 8.025, 0.098, "Покидают систему", size=11.0, weight="bold")

    # Energy labels use dark text on white patches, so no text can disappear on white background.
    label(ax, 4.05, 0.68, "168 МэВ\n(82.8%)", size=13, weight="bold", color="#7f1d1d")
    label(ax, 4.05, 0.485, "7 МэВ\n(3.4%)", size=11.5, weight="bold", color="#7c2d12")
    label(ax, 4.05, 0.34, "13 МэВ\n(6.4%)", size=11.5, weight="bold", color="#7c2d12")
    label(ax, 4.05, 0.225, "5 МэВ\n(2.5%)", size=11.5, weight="bold", color="#0b4778")
    label(ax, 4.05, 0.105, "10 МэВ\n(4.9%)", size=11.5, weight="bold", color="#4b5563")

    plain(ax, 0.85, 0.66, "кинетическая энергия\nосколков деления", size=11, ha="right")
    plain(ax, 0.85, 0.46, "мгновенные $\\gamma$-кванты", size=10.5, ha="right")
    plain(ax, 0.85, 0.33, "запаздывающие $\\beta+\\gamma$\nпродуктов деления", size=10.5, ha="right")
    plain(ax, 0.85, 0.22, "кинетическая энергия\nнейтронов деления", size=10.5, ha="right")
    plain(ax, 0.85, 0.105, "антинейтрино", size=10.5, ha="right")

    plain(ax, 9.05, 0.69, "локально\n(мкм-пробег)", size=11, color="#344054", ha="left")
    plain(ax, 9.05, 0.465, "распределённо", size=11, color="#344054", ha="left")
    plain(ax, 9.05, 0.325, "распределённо,\nс задержкой", size=11, color="#344054", ha="left")
    plain(ax, 9.05, 0.215, "прямой нагрев\nводы", size=11, color="#344054", ha="left")
    plain(ax, 9.05, 0.095, "потеря,\nне депонируется", size=11, color="#344054", ha="left")

    # Right summary bars.
    ax.add_patch(Rectangle((10.95, 0.48), 0.36, 0.38, facecolor="#ead3d3", edgecolor="#cfaaaa", linewidth=1.2))
    ax.add_patch(Rectangle((10.95, 0.20), 0.36, 0.08, facecolor="#d7e4ef", edgecolor="#aec6d9", linewidth=1.2))
    ax.add_patch(Rectangle((10.95, 0.04), 0.36, 0.09, facecolor="#e0e0e0", edgecolor="#c7c7c7", linewidth=1.2))
    plain(ax, 11.13, 0.88, "188 МэВ (94.0%)", size=12, weight="bold", color="#7f1d1d")
    plain(ax, 11.60, 0.67, "НАГРЕВ\nТОПЛИВА\nсоздаёт $T_f$ и\nдоплеровскую\nобратную связь", size=12, weight="bold", color="#7f1d1d", ha="left")
    plain(ax, 11.13, 0.31, "5 МэВ (2.5%)", size=12, weight="bold", color="#0b4778")
    plain(ax, 11.60, 0.24, "НАГРЕВ\nВОДЫ", size=12, weight="bold", color="#0b4778", ha="left")
    plain(ax, 11.13, 0.155, "10 МэВ (5.0%)", size=12, weight="bold", color="#667085")
    plain(ax, 11.60, 0.085, "ПОТЕРЯ", size=12, weight="bold", color="#667085", ha="left")

    plain(
        ax,
        6.6,
        0.015,
        "Смысл для модели: быстрый локальный нагрев топлива формирует $I_D(t)$; вода получает только задержанный тепловой выход $Q_{fw}(t)$.",
        size=10.5,
        color="#475467",
    )

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig8_energy_partition.pdf", bbox_inches="tight", pad_inches=0.08)
    fig.savefig(OUT / "fig8_energy_partition.png", dpi=180, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


if __name__ == "__main__":
    main()
