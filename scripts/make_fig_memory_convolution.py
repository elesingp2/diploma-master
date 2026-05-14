"""Generate fig15_memory_convolution for the memory-kernel section.

        rho_D(t) = - int_0^t K_D(t - s) * P(s) ds.

The figure uses dimensionless values and is intended for the thesis text,
not as a calibrated fuel-pin calculation.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "mathtext.fontset": "dejavusans",
        "axes.titlesize": 12.5,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.dpi": 180,
    }
)

# Time is measured in ms; amplitudes are dimensionless.
T_MAX = 200.0          # plotting horizon, ms
DT = 0.05              # integration step, ms
SIGMA_P = 5.0          # power pulse width, ms
T0_P = 25.0            # power pulse centre, ms
P_AMP = 1.0            # peak excess power

# Two-mode kernel: fast mode + slow mode.
# Coefficients normalised so that integral(K_D) = kappa_D^st = 1.
TAU_FAST = 6.0         # ms  -- inner-fuel diffusive mode
TAU_SLOW = 55.0        # ms  -- outer-fuel / clad-coupled mode
W_FAST = 0.55          # weight of the fast mode in the static gain
W_SLOW = 0.45          # weight of the slow mode in the static gain
KAPPA_ST = W_FAST + W_SLOW  # static gain = 1.0 by construction

T_STAR = 45.0          # snapshot time for panel (c), ms


def power_history(t: np.ndarray) -> np.ndarray:
    """A single excess-power pulse plus a small late shoulder."""
    main = P_AMP * np.exp(-0.5 * ((t - T0_P) / SIGMA_P) ** 2)
    shoulder = 0.18 * P_AMP * np.exp(-0.5 * ((t - 65.0) / 12.0) ** 2)
    return main + shoulder


def kernel(tau: np.ndarray) -> np.ndarray:
    """K_D(tau) = sum_j A_j * exp(-tau/tau_j), causal."""
    A_fast = W_FAST / TAU_FAST
    A_slow = W_SLOW / TAU_SLOW
    k = A_fast * np.exp(-tau / TAU_FAST) + A_slow * np.exp(-tau / TAU_SLOW)
    k[tau < 0] = 0.0
    return k


def memory_response(t_grid: np.ndarray, P: np.ndarray) -> np.ndarray:
    """rho_D(t) = - integral_0^t K_D(t-s) P(s) ds, evaluated on the same
    uniform grid as P (rectangular rule)."""
    n = t_grid.size
    out = np.zeros(n)
    dt = t_grid[1] - t_grid[0]
    # Build full kernel on shifted argument efficiently via discrete
    # convolution.  np.convolve(P, K)[:n] * dt gives the causal response.
    K = kernel(t_grid)  # K_D evaluated at tau = 0..t_max
    full = np.convolve(P, K, mode="full")[:n] * dt
    out = -full
    return out


def quasi_static(P: np.ndarray) -> np.ndarray:
    return -KAPPA_ST * P


def make_figure(out_pdf: Path, out_png: Path) -> None:
    t = np.arange(0.0, T_MAX + DT, DT)
    P = power_history(t)
    K = kernel(t)
    rho_mem = memory_response(t, P)
    rho_qs = quasi_static(P)

    # Snapshot quantities at t*
    idx_star = int(np.round(T_STAR / DT))
    t_star_actual = t[idx_star]
    s_arr = t[: idx_star + 1]
    K_shifted = kernel(t_star_actual - s_arr)
    integrand = K_shifted * P[: idx_star + 1]
    I_D_star = np.trapz(integrand, s_arr)
    rho_D_star = -I_D_star

    # ------------------------------------------------------------------
    # Figure layout: keep only panels (c) and (d).
    # ------------------------------------------------------------------
    fig, (ax_c, ax_d) = plt.subplots(
        1, 2, figsize=(13.5, 4.2), gridspec_kw={"wspace": 0.24},
        constrained_layout=True,
    )

    # =========================================================
    # Panel (c): integrand snapshot at t = t*
    # =========================================================
    # Plot P(s) faintly across the whole horizon
    ax_c.plot(t, P, color="#E65100", lw=1.5, alpha=0.55, label="мощность")

    # Plot K_D(t* - s) reflected & shifted, for s in [0, t*]
    # Scale K_shifted so that its peak matches plot scale (purely visual)
    k_visual_scale = (P_AMP * 0.95) / max(K.max(), 1e-9)
    K_full_shifted = np.zeros_like(t)
    K_full_shifted[: idx_star + 1] = K_shifted
    ax_c.plot(t, K_full_shifted * k_visual_scale, color="#0D47A1", lw=2.0,
              label="сдвинутое ядро")

    # Shaded integrand
    integrand_full = np.zeros_like(t)
    integrand_full[: idx_star + 1] = integrand
    integrand_visual_scale = (P_AMP * 0.95) / max(integrand.max(), 1e-9)
    ax_c.fill_between(t, 0, integrand_full * integrand_visual_scale,
                      color="#7B1FA2", alpha=0.40, lw=0,
                      label="вклад в интеграл")

    # Mark t*
    ax_c.axvline(t_star_actual, color="#212121", ls="--", lw=1.2, alpha=0.85)
    ax_c.text(t_star_actual + 1.5, 1.02 * P_AMP, r"$t^{*}$",
              fontsize=10, color="#212121")

    # Causality shading: future of t*
    ax_c.axvspan(t_star_actual, T_MAX, color="#ECEFF1", alpha=0.55, lw=0)
    ax_c.text(0.5 * (t_star_actual + T_MAX), 1.04 * P_AMP,
              "будущее", fontsize=9, ha="center", va="top",
              color="#455A64")

    ax_c.set_xlim(0, T_MAX)
    ax_c.set_ylim(0, 1.18 * P_AMP)
    ax_c.set_xlabel("время, мс")
    ax_c.set_ylabel("отн. ед.")
    ax_c.set_title(r"(в) Наложение в момент $t^{*}$")
    ax_c.grid(True, ls=":", alpha=0.28)
    ax_c.legend(loc="upper right", fontsize=9, framealpha=0.92)

    # =========================================================
    # Panel (d): output rho_D(t) vs quasi-static
    # =========================================================
    ax_d.plot(t, rho_qs, color="#9E9E9E", lw=2.0, ls="--",
              label="без памяти")
    ax_d.plot(t, rho_mem, color="#0D47A1", lw=2.4,
              label="с памятью")

    # Mark t*
    ax_d.axvline(t_star_actual, color="#212121", ls="--", lw=1.2, alpha=0.85)
    ax_d.text(t_star_actual + 1.5, 0.0, r"$t^{*}$",
              fontsize=10, color="#212121", va="top")

    # Highlight the long memory tail
    ax_d.annotate("хвост памяти",
                  xy=(140, rho_mem[int(140 / DT)]),
                  xytext=(92, -0.66),
                  fontsize=9.5, color="#37474F",
                  arrowprops=dict(arrowstyle="-|>", color="#37474F", lw=1.0,
                                  connectionstyle="arc3,rad=-0.15"))

    ax_d.set_xlim(0, T_MAX)
    ax_d.set_ylim(min(rho_mem.min(), rho_qs.min()) * 1.18, 0.05)
    ax_d.set_xlabel("время, мс")
    ax_d.set_ylabel("реактивность, отн. ед.")
    ax_d.set_title("(г) Отклик реактивности")
    ax_d.grid(True, ls=":", alpha=0.28)
    ax_d.legend(loc="lower right", fontsize=9.5, framealpha=0.95)

    fig.suptitle(
        "Свёртка как память твэла",
        fontsize=13.5, y=0.995,
    )

    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, bbox_inches="tight", dpi=220)
    plt.close(fig)
    print(f"Wrote {out_pdf}")
    print(f"Wrote {out_png}")
    print(f"kappa_D^st = {KAPPA_ST:.3f}")
    print(f"rho_D(t*={t_star_actual:.1f} ms) = {rho_D_star:.4f}")
    print(f"rho_qs(t*) = {-KAPPA_ST * P[idx_star]:.4f}")


if __name__ == "__main__":
    make_figure(
        FIGURES / "fig15_memory_convolution.pdf",
        FIGURES / "fig15_memory_convolution.png",
    )
