"""Generate fig14_thermal_radial_relaxation.

The script solves a 1D radial heat equation for a simplified UO2-gap-Zr fuel
pin after a uniform fuel pulse and plots radial relaxation plus energy
partition between fuel, cladding, and coolant.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib import cm

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "mathtext.fontset": "dejavusans",
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.dpi": 180,
    }
)

# ---------------------------------------------------------------------------
# Geometry (typical LWR fuel pin, simplified: gap collapsed into a
# contact-resistance treatment that we apply as a heat-transfer coefficient
# h_gap between the last fuel cell and the first cladding cell).
# ---------------------------------------------------------------------------
R_FUEL = 4.0e-3        # outer fuel radius [m]
R_GAP_OUT = 4.08e-3    # gap thickness 80 µm
R_CLAD_OUT = 4.68e-3   # cladding thickness 0.6 mm

# Material properties
K_F = 3.5              # UO2 thermal conductivity [W/(m K)]
RHO_CP_F = 3.0e6       # UO2 volumetric heat capacity [J/(m^3 K)]
ALPHA_F = K_F / RHO_CP_F  # ~1.17e-6 m^2/s

K_C = 18.0             # Zircaloy thermal conductivity [W/(m K)]
RHO_CP_C = 2.0e6       # Zircaloy volumetric heat capacity [J/(m^3 K)]
ALPHA_C = K_C / RHO_CP_C  # ~9e-6 m^2/s

H_GAP = 5.0e3          # gap conductance [W/(m^2 K)] (typical Hgap)
H_W = 3.0e4            # convective HTC to water [W/(m^2 K)]
T_W = 580.0            # bulk coolant temperature [K]


def build_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build a piecewise-uniform radial grid; return cell centres r,
    cell widths dr, cell volumes per unit length V = pi*(r_out^2 - r_in^2),
    and a tag array (0 = fuel, 1 = clad)."""
    n_f = 80
    n_c = 30
    r_f = np.linspace(0.0, R_FUEL, n_f + 1)
    r_c = np.linspace(R_GAP_OUT, R_CLAD_OUT, n_c + 1)
    # cell centres
    rc_f = 0.5 * (r_f[:-1] + r_f[1:])
    rc_c = 0.5 * (r_c[:-1] + r_c[1:])
    rc = np.concatenate([rc_f, rc_c])
    # cell widths
    dr_f = np.diff(r_f)
    dr_c = np.diff(r_c)
    dr = np.concatenate([dr_f, dr_c])
    # cell volumes per unit axial length (annulus)
    V_f = np.pi * (r_f[1:] ** 2 - r_f[:-1] ** 2)
    V_c = np.pi * (r_c[1:] ** 2 - r_c[:-1] ** 2)
    V = np.concatenate([V_f, V_c])
    # tags
    tag = np.zeros_like(rc, dtype=int)
    tag[n_f:] = 1
    return rc, dr, V, tag


def step(T: np.ndarray, rc: np.ndarray, dr: np.ndarray, V: np.ndarray,
         tag: np.ndarray, dt: float) -> np.ndarray:
    """One explicit FTCS step on the cylindrical grid."""
    n = T.size
    # Material arrays
    k = np.where(tag == 0, K_F, K_C)
    rho_cp = np.where(tag == 0, RHO_CP_F, RHO_CP_C)

    # Conductive flux at internal interfaces between same-material cells.
    # Use harmonic mean conductivity for cell pairs.
    # Interface index i corresponds to boundary between cell i and i+1.
    flux = np.zeros(n + 1)
    # Inner symmetry: flux[0] = 0
    # Outer water boundary: convective
    # Internal interfaces
    for i in range(n - 1):
        # Skip the gap interface: handled via H_GAP
        same_material = tag[i] == tag[i + 1]
        # interface radius
        r_if = 0.5 * (rc[i] + rc[i + 1])
        if same_material:
            # harmonic mean
            kh = 2.0 * k[i] * k[i + 1] / (k[i] + k[i + 1])
            grad = (T[i + 1] - T[i]) / (rc[i + 1] - rc[i])
            # area per unit length = 2*pi*r_if
            flux[i + 1] = -kh * grad * (2.0 * np.pi * r_if)
        else:
            # fuel-clad gap: Newton's law with H_GAP at r = R_FUEL surface
            # Use the area at the actual fuel outer surface
            q_pp = H_GAP * (T[i] - T[i + 1])
            flux[i + 1] = q_pp * (2.0 * np.pi * R_FUEL)
    # Outer water boundary
    q_pp_w = H_W * (T[-1] - T_W)
    flux[-1] = q_pp_w * (2.0 * np.pi * R_CLAD_OUT)

    # Net energy change per unit length per cell (W/m): dE/dt = -(flux_out - flux_in)
    dE = -(flux[1:] - flux[:-1])
    dT = dE * dt / (rho_cp * V)
    return T + dT


def cfl_dt(rc: np.ndarray, dr: np.ndarray, tag: np.ndarray) -> float:
    """Stability dt for explicit FTCS in cylindrical coords."""
    alpha = np.where(tag == 0, ALPHA_F, ALPHA_C)
    return 0.4 * np.min(dr ** 2 / alpha)


def simulate(T_pulse: float, t_max: float) -> dict:
    rc, dr, V, tag = build_grid()
    n = rc.size
    # Initial state: uniform pulse in fuel, equilibrium elsewhere.
    # We track DELTA T relative to the steady-state solution.  For clarity,
    # set T_w = T_W and start fuel + clad at T_W + 0 then deposit pulse.
    T = np.full(n, T_W)
    # Add T_pulse to fuel cells
    T[tag == 0] += T_pulse

    dt = cfl_dt(rc, dr, tag)

    # Snapshot times (geometric)
    snapshots = [1e-3, 1e-2, 1e-1, 5e-1, 2.0, 10.0]
    snapshots = [s for s in snapshots if s <= t_max]
    snap_times = []
    snap_T = []

    # Energy partition tracking
    rho_cp = np.where(tag == 0, RHO_CP_F, RHO_CP_C)
    E_fuel0 = np.sum((T[tag == 0] - T_W) * rho_cp[tag == 0] * V[tag == 0])

    log_times = np.geomspace(1e-4, t_max, 200)
    e_fuel_t = np.zeros_like(log_times)
    e_clad_t = np.zeros_like(log_times)
    e_water_t = np.zeros_like(log_times)

    t = 0.0
    next_snap = 0
    next_log = 0
    # take initial snapshot at very small t
    T0_snap = T.copy()

    while t < t_max:
        # determine if we cross next snapshot
        T = step(T, rc, dr, V, tag, dt)
        t += dt

        while next_snap < len(snapshots) and t >= snapshots[next_snap]:
            snap_times.append(t)
            snap_T.append(T.copy())
            next_snap += 1

        while next_log < len(log_times) and t >= log_times[next_log]:
            E_fuel = np.sum((T[tag == 0] - T_W) * rho_cp[tag == 0] * V[tag == 0])
            E_clad = np.sum((T[tag == 1] - T_W) * rho_cp[tag == 1] * V[tag == 1])
            e_fuel_t[next_log] = E_fuel / E_fuel0
            e_clad_t[next_log] = E_clad / E_fuel0
            e_water_t[next_log] = 1.0 - (E_fuel + E_clad) / E_fuel0
            next_log += 1

    # Trim unfilled trailing entries if any
    valid = next_log
    return {
        "rc": rc,
        "tag": tag,
        "snapshots": snap_times,
        "snap_T": snap_T,
        "T0": T0_snap,
        "log_times": log_times[:valid],
        "e_fuel": e_fuel_t[:valid],
        "e_clad": e_clad_t[:valid],
        "e_water": e_water_t[:valid],
        "alpha_f": ALPHA_F,
    }


def make_figure(out_path: Path, png_path: Path) -> None:
    sim = simulate(T_pulse=200.0, t_max=10.0)

    rc_mm = sim["rc"] * 1e3

    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.6),
                             gridspec_kw={"width_ratios": [1.15, 1.0]})

    # =========================================================
    # Panel (a): radial temperature profiles
    # =========================================================
    ax = axes[0]

    # Coloured background bands for materials
    ax.axvspan(0, R_FUEL * 1e3, color="#FFE0B2", alpha=0.55, zorder=0)
    ax.axvspan(R_FUEL * 1e3, R_GAP_OUT * 1e3, color="#ECEFF1", alpha=0.95, zorder=0)
    ax.axvspan(R_GAP_OUT * 1e3, R_CLAD_OUT * 1e3, color="#CFD8DC", alpha=0.85, zorder=0)
    ax.axvspan(R_CLAD_OUT * 1e3, 5.6, color="#BBDEFB", alpha=0.55, zorder=0)

    # Material labels (inside axis, top edge)
    for x, lbl in [
        (R_FUEL * 1e3 / 2, r"UO$_2$"),
        ((R_FUEL + R_GAP_OUT) * 1e3 / 2, "He gap"),
        ((R_GAP_OUT + R_CLAD_OUT) * 1e3 / 2, "Zr"),
        ((R_CLAD_OUT * 1e3 + 5.6) / 2, r"H$_2$O"),
    ]:
        ax.text(x, 0.965, lbl, transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=10, color="#263238",
                fontweight="bold")

    # Initial pulse profile (uniform DT in fuel, 0 elsewhere)
    T0_curve = np.where(sim["tag"] == 0, 200.0, 0.0)
    ax.plot(rc_mm, T0_curve, color="#B71C1C", lw=2.6,
            label=r"$t=0^{+}$  (импульс)")

    cmap = plt.get_cmap("viridis")
    n_snap = len(sim["snapshots"])
    for i, (t, T) in enumerate(zip(sim["snapshots"], sim["snap_T"])):
        c = cmap(0.15 + 0.7 * i / max(n_snap - 1, 1))
        if t < 1.0:
            label = f"t = {t*1e3:.0f} мс"
        else:
            label = f"t = {t:.1f} с"
        ax.plot(rc_mm, T - T_W, color=c, lw=1.9, label=label)

    # Set y-limits before adding markers below the data area
    ax.set_ylim(-30, 230)

    # Diffusion length markers √(alpha_f * t): show how far heat has traveled
    y_marker = -15
    for i, t in enumerate(sim["snapshots"]):
        ell = np.sqrt(sim["alpha_f"] * t) * 1e3  # mm
        if ell > 5.5:
            continue
        c = cmap(0.15 + 0.7 * i / max(n_snap - 1, 1))
        # downward triangle marker pointing up at diffusion-front position
        ax.scatter([ell], [y_marker], marker="^", s=80, color=c,
                   edgecolor="#212121", lw=0.7, zorder=5)
    ax.text(5.35, y_marker, r"$\sqrt{\alpha_f\,t}$ — фронт",
            color="#37474F", fontsize=9, ha="right", va="center")

    # Vertical interface markers
    for x in (R_FUEL * 1e3, R_GAP_OUT * 1e3, R_CLAD_OUT * 1e3):
        ax.axvline(x, color="#607D8B", lw=0.8, ls="--", zorder=1, alpha=0.7)

    ax.set_xlim(0, 5.4)
    ax.set_xlabel("радиус r, мм", fontsize=11)
    ax.set_ylabel(r"$\Delta T_f(r,t)$, К  (отклонение от равновесия с водой)",
                  fontsize=11)
    ax.set_title(r"(а) Радиальная релаксация теплового следа $\Delta T_f(r,t)$",
                 fontsize=12, pad=10)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.95, ncol=1)
    ax.grid(True, ls=":", alpha=0.45)

    # =========================================================
    # Panel (b): energy partition and timescale annotations
    # =========================================================
    ax2 = axes[1]
    ax2.set_xscale("log")
    ax2.fill_between(sim["log_times"], 0, sim["e_fuel"],
                     color="#FB8C00", alpha=0.60, label=r"в объёме топлива")
    ax2.fill_between(sim["log_times"], sim["e_fuel"],
                     sim["e_fuel"] + sim["e_clad"],
                     color="#90A4AE", alpha=0.60, label=r"в оболочке Zr")
    ax2.fill_between(sim["log_times"], sim["e_fuel"] + sim["e_clad"], 1.0,
                     color="#1E88E5", alpha=0.45, label=r"ушло в воду")

    ax2.plot(sim["log_times"], sim["e_fuel"], color="#E65100", lw=2.2)
    ax2.plot(sim["log_times"], sim["e_fuel"] + sim["e_clad"],
             color="#263238", lw=2.2)

    # Characteristic times
    tau_diff = R_FUEL ** 2 / sim["alpha_f"]
    ax2.axvline(tau_diff, color="#212121", ls="--", lw=1.1, alpha=0.85)
    ax2.text(tau_diff * 0.92, 0.50,
             r"$\tau_{\mathrm{diff}}=R_f^2/\alpha_f\approx %.1f\;\mathrm{с}$" % tau_diff,
             rotation=90, va="center", ha="right", fontsize=10, color="#212121")

    # Annotate Doppler vs water "windows"
    ax2.annotate(r"окно $K_D(t)$:" "\n" r"объёмный нагрев топлива",
                 xy=(3e-3, 0.97), xytext=(2e-4, 0.62),
                 fontsize=10, color="#BF360C", ha="left",
                 arrowprops=dict(arrowstyle="-|>", color="#BF360C", lw=1.1,
                                 connectionstyle="arc3,rad=0.15"))
    ax2.annotate(r"окно $H_{fw}(t)$:" "\n" r"выход энергии к воде",
                 xy=(5.0, 0.78), xytext=(0.6, 0.20),
                 fontsize=10, color="#0D47A1", ha="left",
                 arrowprops=dict(arrowstyle="-|>", color="#0D47A1", lw=1.1,
                                 connectionstyle="arc3,rad=-0.2"))

    ax2.set_xlim(sim["log_times"][0], sim["log_times"][-1])
    ax2.set_ylim(0, 1.0)
    ax2.set_xlabel("время t, с (логарифмическая шкала)", fontsize=11)
    ax2.set_ylabel("доля энергии импульса", fontsize=11)
    ax2.set_title(r"(б) Разделение энергии импульса по объёмам",
                  fontsize=12, pad=10)
    ax2.legend(loc="upper left", fontsize=9, framealpha=0.95)
    ax2.grid(True, which="both", ls=":", alpha=0.45)

    fig.suptitle(
        "Эволюция теплового следа в твэле после импульса мощности: "
        "доплеровский и водный каналы живут на разных временах",
        fontsize=13.5, y=0.995,
    )

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    fig.savefig(png_path, bbox_inches="tight", dpi=220)
    plt.close(fig)
    print(f"Wrote {out_path}")
    print(f"Wrote {png_path}")
    # Diagnostics
    print(f"alpha_f = {ALPHA_F:.3e} m^2/s")
    print(f"tau_diff = R_f^2/alpha_f = {R_FUEL ** 2 / ALPHA_F:.2f} s")
    print(f"sqrt(alpha_f * 1e-3) = {np.sqrt(ALPHA_F * 1e-3) * 1e6:.1f} um (in 1 ms)")


if __name__ == "__main__":
    make_figure(
        FIGURES / "fig14_thermal_radial_relaxation.pdf",
        FIGURES / "fig14_thermal_radial_relaxation.png",
    )
