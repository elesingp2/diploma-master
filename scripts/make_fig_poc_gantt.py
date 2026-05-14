from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


OUT = Path("figures")


def rounded_bar(ax, x, y, width, color, title, result):
    bar = FancyBboxPatch(
        (x, y - 0.22),
        width,
        0.44,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        linewidth=0,
        facecolor=color,
        alpha=0.95,
    )
    ax.add_patch(bar)
    ax.text(x + 0.08, y + 0.035, title, ha="left", va="center", fontsize=8.8, color="#172026")
    ax.text(x + 0.08, y - 0.14, result, ha="left", va="center", fontsize=7.5, color="#3c4b55")


def main():
    OUT.mkdir(exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.6, 3.55))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f7f8f6")

    ax.set_xlim(-0.15, 6.85)
    ax.set_ylim(-0.75, 4.85)

    stages = [
        (0.05, 4.0, 1.55, "#7bb6a4", "Образец и диагностика", r"калибровка $T$ и $E_{\mathrm{вв}}$"),
        (1.25, 3.0, 1.45, "#d8a15d", "Инертный импульс", r"$T_c(t)$, целостность"),
        (2.35, 2.0, 2.05, "#6f9ed6", "Вода или пар под давлением", r"$T_s(t)$, $q''$, $p(t)$"),
        (3.85, 1.0, 1.05, "#9f8cc5", "Газ и конденсат", r"следы $H_2$"),
        (4.55, 0.0, 1.35, "#c98787", "Образец после опыта", "окисление, трещины"),
        (5.55, 2.9, 0.95, "#6d7580", "Критерий", "решение"),
    ]
    for item in stages:
        rounded_bar(ax, *item)

    # Light dependency lines: the diagram is read as an experimental sequence,
    # not as a calendar schedule.
    arrows = [
        ((1.50, 3.78), (1.58, 3.24)),
        ((2.55, 2.82), (2.72, 2.23)),
        ((4.05, 1.78), (4.18, 1.24)),
        ((4.85, 0.78), (4.98, 0.24)),
        ((5.65, 0.35), (5.85, 2.55)),
        ((4.15, 2.23), (5.55, 2.78)),
    ]
    for (x0, y0), (x1, y1) in arrows:
        ax.annotate(
            "",
            xy=(x1, y1),
            xytext=(x0, y0),
            arrowprops=dict(arrowstyle="-|>", color="#9aa3a3", lw=1.1, shrinkA=2, shrinkB=2),
        )

    ax.axvline(6.55, ymin=0.11, ymax=0.84, color="#5d666b", lw=1.1, ls=(0, (4, 3)))
    ax.text(6.44, 4.25, "граница\nэтапа", ha="center", va="center", fontsize=7.8, color="#3b4448")
    ax.set_title("Опытный этап проверки принципа", loc="left", fontsize=10.2, color="#16212a", weight="bold", pad=8)

    ax.set_yticks([])
    ax.set_xticks([0, 1, 2, 3, 4, 5, 6])
    ax.set_xticklabels(
        ["0", "1", "2", "3", "4", "5", "6"],
        fontsize=8,
        color="#58636a",
    )
    ax.set_xlabel("условная последовательность испытательного этапа", fontsize=8.5, color="#58636a")
    ax.tick_params(axis="x", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="x", color="white", lw=1.2)

    fig.subplots_adjust(left=0.055, right=0.985, top=0.86, bottom=0.17)
    fig.savefig(OUT / "fig17_poc_gantt.pdf")
    fig.savefig(OUT / "fig17_poc_gantt.png", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    main()
