"""Matplotlib figure builders. Styled for paper reuse (SVG-friendly, no web fonts)."""

from __future__ import annotations

import io
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

NAVY = "#0b3c5d"
TEAL = "#0e6f8e"
CYAN = "#2ea3a0"
GOLD = "#c2691e"
RED = "#b91c1c"
GREEN = "#0f7b5f"
GREY = "#5b6b7a"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.edgecolor": NAVY,
    "axes.labelcolor": NAVY,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 130,
    "savefig.bbox": "tight",
})


def fig_to_png_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    return buf.getvalue()


def fig_rate_qber_vs_distance(ci, cfg):
    from .qkd import evaluate_at_distance
    ds = np.linspace(1.0, 20.0, 96)
    r_bb, r_dc, qber = [], [], []
    from .qkd import QKDConfig
    cfg_bb = QKDConfig(**{**cfg.as_dict(), "protocol": "BB84 (ideal source, simplified)"})
    for d in ds:
        r_dc.append(evaluate_at_distance(ci, cfg, d)["secure_rate_bps"] / 1e3)
        r_bb.append(evaluate_at_distance(ci, cfg_bb, d)["secure_rate_bps"] / 1e3)
        qber.append(evaluate_at_distance(ci, cfg, d)["qber_percent"])
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.plot(ds, r_bb, color=CYAN, ls="--", lw=1.4, label="BB84 (idealised)")
    ax.plot(ds, r_dc, color=TEAL, lw=2.2, label="Decoy-state BB84 (simplified)")
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Secure-key rate (kbit/s)")
    ax.set_xlim(1, 20)
    ax.set_ylim(bottom=0)
    ax2 = ax.twinx()
    ax2.plot(ds, qber, color=RED, lw=1.3, alpha=0.75, label="QBER (right)")
    ax2.axhline(11.0, color=RED, lw=1.0, ls=":", alpha=0.8)
    ax2.set_ylabel("QBER (%)")
    ax2.set_ylim(0, max(15.0, float(np.nanmax(qber)) * 1.1))
    ax2.spines["right"].set_visible(True)
    l1, lab1 = ax.get_legend_handles_labels()
    l2, lab2 = ax2.get_legend_handles_labels()
    ax.legend(l1 + l2, lab1 + lab2, loc="upper right", frameon=False, fontsize=8)
    ax.set_title("Secure-key rate and QBER vs. link distance")
    ax.grid(axis="y", ls=":", alpha=0.4)
    fig.tight_layout()
    return fig


def fig_rate_vs_ntu(ci, cfg):
    from .qkd import evaluate_at_distance
    from .waters import WATER_TYPES
    import dataclasses
    ntus = np.linspace(0, 100, 80)
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    for name, meta in WATER_TYPES.items():
        ci2 = dataclasses.replace(ci, ntu=float(ntus[0]), water_type=name)
        rates = []
        for ntu in ntus:
            ci2 = dataclasses.replace(ci, ntu=float(ntu), water_type=name)
            rates.append(evaluate_at_distance(ci2, cfg, ci2.distance_m)["secure_rate_bps"] / 1e3)
        ax.plot(ntus, rates, color=meta["color"], lw=2.0, label=name)
    ax.set_xlabel("Turbidity (NTU)")
    ax.set_ylabel("Secure-key rate (kbit/s)")
    ax.set_xlim(0, 100)
    ax.set_ylim(bottom=0)
    ax.set_title(f"Secure-key rate vs. turbidity at L = {ci.distance_m:.1f} m")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(ls=":", alpha=0.4)
    fig.tight_layout()
    return fig


def fig_transmittance_waterfall(ch):
    nano_db = ch.get("nano_loss_db", 0.0) if ch.get("nanophotonic") else 0.0
    labels = ["Absorption", "Scattering", "Geometric spread", "Misalignment"]
    losses = [ch["beer_loss_absorption_db"], ch["beer_loss_scattering_db"],
              ch["geo_loss_db"], ch["mis_loss_db"]]
    if nano_db:
        labels.append("Nanophotonic (net)")
        losses.append(nano_db)
    labels.append("Detector efficiency")
    losses.append(-10.0 * np.log10(max(ch["detector_efficiency"], 1e-12)))
    total = sum(losses)
    losses = [max(v, 0.0) for v in losses]
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    y = np.arange(len(labels) + 1)
    vals = losses + [total]
    cols = [CYAN, GOLD, TEAL, GREEN] + (["#8e44ad"] if nano_db else []) + [GREY, NAVY]
    bars = ax.barh(y, vals, color=cols, edgecolor="white")
    ax.set_yticks(y)
    ax.set_yticklabels(labels + ["TOTAL LINK LOSS"])
    ax.invert_yaxis()
    ax.set_xlabel("Loss (dB)")
    ax.set_title("Transmittance budget (water + pointing + detector)")
    for b, v in zip(bars, vals):
        ax.text(v + total * 0.01, b.get_y() + b.get_height() / 2, f"{(0.0 if abs(v) < 0.05 else v):.1f} dB",
                va="center", fontsize=8, color=NAVY)
    ax.set_xlim(0, total * 1.18)
    ax.grid(axis="x", ls=":", alpha=0.4)
    fig.tight_layout()
    return fig


def fig_mu_sweep(ci, cfg):
    from .qkd import evaluate_at_distance, QKDConfig
    mus = np.linspace(0.05, 0.8, 76)
    rates = []
    for mu in mus:
        cfg2 = QKDConfig(**{**cfg.as_dict(), "mu": float(mu)})
        rates.append(evaluate_at_distance(ci, cfg2, ci.distance_m)["secure_bits_per_pulse"])
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.plot(mus, rates, color=TEAL, lw=2.2)
    imax = int(np.argmax(rates))
    ax.scatter([mus[imax]], [rates[imax]], color=GOLD, zorder=5,
               label=f"optimum μ ≈ {mus[imax]:.2f}")
    ax.axhline(0, color=GREY, lw=0.8, ls="--")
    ax.set_xlabel("Mean photon number μ")
    ax.set_ylabel("Secure bits per pulse")
    ax.set_title("Secure-key rate vs. pulse intensity")
    ax.legend(frameon=False)
    ax.grid(ls=":", alpha=0.4)
    fig.tight_layout()
    return fig


def fig_eve_analysis(ch, cfg):
    from .qkd import evaluate_qkd, QKDConfig, h2
    fr = np.linspace(0, 1, 101)
    qbers = []
    for f in fr:
        cfg2 = QKDConfig(**{**cfg.as_dict(), "eve_fraction": float(f)})
        qbers.append(evaluate_qkd(ch, cfg2)["qber_percent"])
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.plot(fr * 100, qbers, color=RED, lw=2.2)
    ax.axhline(11.0, color=RED, ls=":", lw=1.2, alpha=0.8, label="11 % BB84 threshold")
    ax.set_xlabel("Intercepted fraction of pulses (%)")
    ax.set_ylabel("QBER (%)")
    ax.set_title("Intercept-resend: QBER vs. interception fraction")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, max(30, float(np.nanmax(qbers)) * 1.1))
    ax.legend(frameon=False)
    ax.grid(ls=":", alpha=0.4)
    fig.tight_layout()
    return fig


def fig_secret_fraction():
    from .qkd import h2
    es = np.linspace(0, 0.15, 200)
    h = np.array([h2(float(e)) for e in es])
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.plot(es * 100, 1 - 2 * h, color=TEAL, lw=2.0,
            label="Ideal (f = 1): 1 − 2·H₂(e)")
    ax.plot(es * 100, 1 - 2.16 * h, color=GOLD, lw=2.0, ls="--",
            label="Practical (f = 1.16): 1 − 2.16·H₂(e)")
    ax.axhline(0, color=GREY, ls=":", lw=1.0)
    ax.set_xlabel("QBER e (%)")
    ax.set_ylabel("Secret fraction")
    ax.set_title("Asymptotic secret fraction vs. QBER")
    ax.legend(frameon=False)
    ax.grid(ls=":", alpha=0.4)
    fig.tight_layout()
    return fig


def fig_lines(x, series: dict, xlabel: str, ylabel: str, title: str,
              styles=None, ymin0: bool = True):
    """Generic multi-series line figure. series = {label: y_list}."""
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    default_colors = [CYAN, GOLD, TEAL, GREEN, RED, GREY]
    for i, (label, y) in enumerate(series.items()):
        color = default_colors[i % len(default_colors)]
        ls = ["-", "--", "-.", ":"][i % 4]
        ax.plot(x, y, color=color, lw=2.1, ls=ls, marker="o", ms=3.5, label=label)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    if ymin0:
        ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=8); ax.grid(ls=":", alpha=0.4)
    fig.tight_layout()
    return fig
