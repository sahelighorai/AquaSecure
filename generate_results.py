"""Batch experiment campaign for the Testing/Results/Discussion section.
All numbers are computed from the AquaSecure engine (aquasecure/ package)."""
import sys, json, math, dataclasses
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from aquasecure.channel import ChannelInput, evaluate_channel
from aquasecure.qkd import QKDConfig, evaluate_qkd, evaluate_at_distance, max_secure_distance, optimal_mu, h2
from aquasecure.mc import run_bb84_mc
from aquasecure.waters import WATER_TYPES, BACKGROUND_LEVELS
from aquasecure.figures import (fig_transmittance_waterfall, fig_eve_analysis,
                                fig_secret_fraction, fig_to_png_bytes,
                                NAVY, TEAL, CYAN, GOLD, RED, GREEN, GREY)

FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
OUT = {}

def base_ci(**kw):
    d = dict(water_type="Coastal ocean", distance_m=5.0, ntu=20.0,
             background="Night (moonless)", detector_efficiency=0.15,
             dark_count_cps=100.0, clock_hz=1e7, misalignment_mrad=0.5,
             divergence_mrad=10.0, tx_aperture_radius_m=0.02,
             rx_aperture_radius_m=0.05, k_ntu=0.05)
    d.update(kw); return ChannelInput(**d)

cfg = QKDConfig(protocol="Decoy-state BB84", mu=0.5, decoy_nu=0.1, f_ec=1.16,
                e_intrinsic=0.015, eve_fraction=0.0)

# ---------- 1) Baseline budget (coastal, 5 m, 20 NTU, night)
ci = base_ci()
ch = evaluate_channel(ci); ev = evaluate_qkd(ch, cfg)
OUT["baseline"] = {k: ch[k] for k in ["attenuation_c","beer_loss_db","beer_loss_absorption_db",
                   "beer_loss_scattering_db","scattering_ntu_b","geo_loss_db","mis_loss_db",
                   "eta_beer","eta_geo","eta_mis","eta_channel","eta_total",
                   "channel_loss_db","total_loss_db","y0","bg_photons_per_gate","dark_counts_per_gate"]}
OUT["baseline_ev"] = {k: ev[k] for k in ["q_mu","qber_percent","received_rate_cps","sifted_rate_bps",
                     "secure_rate_bps","secure_bits_per_pulse","security_status",
                     "y1_lower_bound","q1_lower_bound","e1_upper_bound"]}
print("baseline", OUT["baseline"]); print("baseline_ev", OUT["baseline_ev"])

fig = fig_transmittance_waterfall(ch); fig.savefig(f"{FIG}/fig1_budget.png", dpi=200); plt.close(fig)

# ---------- 2) Distance sweep: R_sec & QBER for 4 water types, NTU in {0,25,50}
dists = [1,2,3,5,7,10,13,15,17,20]
table_dist = {}
for wt in WATER_TYPES:
    table_dist[wt] = {}
    for ntu in (0,25,50):
        row = []
        for d in dists:
            r = evaluate_at_distance(base_ci(water_type=wt, distance_m=float(d), ntu=float(ntu)), cfg, float(d))
            row.append({"L": d, "R_kbps": r["secure_rate_bps"]/1e3, "qber": r["qber_percent"],
                        "status": r["security_status"]})
        table_dist[wt][str(ntu)] = row
OUT["distance_table"] = table_dist

# Figure: secure rate vs distance at NTU=25 (4 water types)
ds = np.linspace(1,20,96)
fig, ax = plt.subplots(figsize=(7.6,4.2))
for wt, meta in WATER_TYPES.items():
    rates = [max(evaluate_at_distance(base_ci(water_type=wt, distance_m=float(d), ntu=25.0), cfg, float(d))["secure_rate_bps"],0)/1e3 for d in ds]
    ax.plot(ds, rates, color=meta["color"], lw=2.1, label=wt)
ax.set_xlabel("Distance (m)"); ax.set_ylabel("Secure-key rate (kbit/s)")
ax.set_title("Secure-key rate vs. distance at 25 NTU, night, decoy-state BB84")
ax.set_xlim(1,20); ax.set_ylim(bottom=0); ax.legend(frameon=False); ax.grid(ls=":", alpha=.4)
fig.tight_layout(); fig.savefig(f"{FIG}/fig2_rate_vs_distance.png", dpi=200); plt.close(fig)

# ---------- 3) Heatmaps: secure rate over distance × NTU
heat = {}
fig, axes = plt.subplots(1, 4, figsize=(13.5, 3.6), sharey=True)
ntus = np.arange(0, 101, 10)
# First pass: compute all panels so the colour scale is GLOBAL (comparable)
_allZ = {}
for wt in WATER_TYPES:
    Z = np.zeros((len(ntus), 20))
    for i, ntu in enumerate(ntus):
        for j, L in enumerate(range(1, 21)):
            r = evaluate_at_distance(base_ci(water_type=wt, distance_m=float(L), ntu=float(ntu)), cfg, float(L))
            Z[i, j] = max(r["secure_rate_bps"]/1e3, 0.0)
    _allZ[wt] = Z
_global_vmax = max(Z[Z > 0].max() for Z in _allZ.values())
for ax, (wt, meta) in zip(axes, WATER_TYPES.items()):
    Z = _allZ[wt]
    heat[wt] = Z.tolist()
    Zm = np.where(Z <= 0.0, np.nan, Z)
    cmap = plt.get_cmap("YlGnBu").copy()
    cmap.set_bad("#ececec")
    im = ax.imshow(Zm, origin="lower", aspect="auto", cmap=cmap,
                   norm=LogNorm(vmin=0.01, vmax=_global_vmax))
    ax.set_title(wt, fontsize=9); ax.set_xlabel("Distance (m)")
    ax.set_xticks([0, 4, 9, 14, 19]); ax.set_xticklabels(["1","5","10","15","20"])
axes[0].set_ylabel("Turbidity (NTU)"); axes[0].set_yticks(range(len(ntus))); axes[0].set_yticklabels(ntus)
fig.suptitle("Secure-key rate (kbit/s, log scale) — distance × turbidity  (grey = no key, abort)", fontsize=9)
fig.colorbar(im, ax=axes, shrink=0.85, label="kbit/s")
fig.savefig(f"{FIG}/fig3_heatmap.png", dpi=200); plt.close(fig)
OUT["heatmaps"] = {"ntus": list(ntus), "grid": heat}

# ---------- 4) L_max vs NTU
lmax_tbl = {}
for wt in WATER_TYPES:
    lmax_tbl[wt] = {}
    for ntu in (0, 10, 25, 50, 75, 100):
        lm = max_secure_distance(base_ci(water_type=wt, distance_m=1.0, ntu=float(ntu)), cfg)
        lmax_tbl[wt][str(ntu)] = lm
OUT["lmax_vs_ntu"] = lmax_tbl
fig, ax = plt.subplots(figsize=(7.6, 4.2))
ntu_axis = np.arange(0, 101, 10)
for wt, meta in WATER_TYPES.items():
    ys = [max_secure_distance(base_ci(water_type=wt, distance_m=1.0, ntu=float(n)), cfg) or 0.0 for n in ntu_axis]
    ax.plot(ntu_axis, ys, marker="o", ms=4, lw=1.8, color=meta["color"], label=wt)
ax.set_xlabel("Turbidity (NTU)"); ax.set_ylabel("Maximum secure distance (m)")
ax.set_title("L_max vs. turbidity (night, decoy-state BB84, η_det = 15 %)")
ax.set_xlim(0,100); ax.set_ylim(bottom=0); ax.legend(frameon=False); ax.grid(ls=":", alpha=.4)
fig.tight_layout(); fig.savefig(f"{FIG}/fig4_lmax_vs_ntu.png", dpi=200); plt.close(fig)

# ---------- 5) Background lighting comparison (coastal, NTU 20)
bg_tbl = {}
for bg in BACKGROUND_LEVELS:
    bg_tbl[bg] = {}
    for L in (5, 10):
        r = evaluate_at_distance(base_ci(distance_m=float(L), ntu=20.0, background=bg), cfg, float(L))
        bg_tbl[bg][str(L)] = {"qber": r["qber_percent"], "R_kbps": r["secure_rate_bps"]/1e3,
                              "status": r["security_status"], "y0": None}
        bg_tbl[bg][str(L)]["y0"] = evaluate_channel(base_ci(distance_m=float(L), ntu=20.0, background=bg))["y0"]
OUT["background"] = bg_tbl

fig, ax = plt.subplots(figsize=(7.6, 4.0))
bgs = list(BACKGROUND_LEVELS); xpos = np.arange(len(bgs))
r5 = [max(bg_tbl[b]["5"]["R_kbps"], 0) for b in bgs]
r10 = [max(bg_tbl[b]["10"]["R_kbps"], 0) for b in bgs]
ax.bar(xpos-0.2, r5, 0.36, label="L = 5 m", color=TEAL)
ax.bar(xpos+0.2, r10, 0.36, label="L = 10 m", color=GOLD)
ax.set_xticks(xpos); ax.set_xticklabels(["Night","Artificial","Daylight"])
ax.set_ylabel("Secure-key rate (kbit/s)"); ax.set_title("Effect of background light (coastal, 20 NTU)")
ax.legend(frameon=False); ax.grid(axis="y", ls=":", alpha=.4)
fig.tight_layout(); fig.savefig(f"{FIG}/fig5_background.png", dpi=200); plt.close(fig)

# ---------- 6) Protocol comparison (coastal, NTU 20)
cfg_bb = QKDConfig(**{**cfg.as_dict(), "protocol": "BB84 (ideal source, simplified)"})
proto_tbl = {}
for L in (5, 10, 15):
    r_d = evaluate_at_distance(base_ci(distance_m=float(L), ntu=20.0), cfg, float(L))
    r_b = evaluate_at_distance(base_ci(distance_m=float(L), ntu=20.0), cfg_bb, float(L))
    proto_tbl[str(L)] = {"decoy_kbps": r_d["secure_rate_bps"]/1e3, "bb84_kbps": r_b["secure_rate_bps"]/1e3,
                         "decoy_qber": r_d["qber_percent"], "bb84_qber": r_b["qber_percent"],
                         "decoy_status": r_d["security_status"], "bb84_status": r_b["security_status"]}
OUT["protocol"] = proto_tbl

# ---------- 7) Intercept-resend: QBER vs interception fraction
eve_rows = []
for f in (0.0, 0.1, 0.25, 0.36, 0.5, 0.75, 1.0):
    c2 = QKDConfig(**{**cfg.as_dict(), "eve_fraction": f})
    r = evaluate_at_distance(base_ci(distance_m=5.0, ntu=20.0), c2, 5.0)
    eve_rows.append({"f": f, "qber": r["qber_percent"], "R_kbps": r["secure_rate_bps"]/1e3, "status": r["security_status"]})
e_base = evaluate_at_distance(base_ci(distance_m=5.0, ntu=20.0), cfg, 5.0)["e_mu"]
OUT["eve"] = {"rows": eve_rows, "e_base": 100*e_base, "f_crit_analytical": (0.11 - e_base)/0.25}
fig = fig_eve_analysis(evaluate_channel(base_ci()), cfg)
fig.savefig(f"{FIG}/fig6_eve.png", dpi=200); plt.close(fig)

# ---------- 8) MC vs analytic across 10 seeds
mc_rows = []
for seed in range(10):
    r = run_bb84_mc(250_000, cfg.mu, ch["eta_total"], ch["y0"], ev["e_d_effective"], 0.0, seed)
    mc_rows.append(r)
qbers = np.array([r["qber_percent"] for r in mc_rows])
yields_ = np.array([r["detection_yield"] for r in mc_rows])
sifted = np.array([r["sifted_fraction"] for r in mc_rows])
OUT["mc"] = {
    "n_pulses": 250_000, "seeds": list(range(10)),
    "qber_mean": float(qbers.mean()), "qber_std": float(qbers.std()),
    "yield_mean": float(yields_.mean()), "yield_std": float(yields_.std()),
    "sifted_mean": float(sifted.mean()), "sifted_std": float(sifted.std()),
    "analytic_qber": ev["qber_percent"], "analytic_yield": ev["q_mu"],
    "analytic_sifted": ev["sifted_bits_per_pulse"],
    "qber_abs_dev_pct": float(abs(qbers.mean() - ev["qber_percent"])),
    "yield_rel_err_pct": float(100*abs(yields_.mean() - ev["q_mu"])/ev["q_mu"]),
}
fig, ax = plt.subplots(figsize=(7.4, 3.6))
labels = ["Detection yield (×10³)", "QBER (%)", "Sifted / pulse (×10³)"]
analytic = [1e3*ev["q_mu"], ev["qber_percent"], 1e3*ev["sifted_bits_per_pulse"]]
mc = [1e3*yields_.mean(), qbers.mean(), 1e3*sifted.mean()]
mc_err = [1e3*yields_.std(), qbers.std(), 1e3*sifted.std()]
x = np.arange(3)
ax.bar(x-0.2, analytic, 0.36, label="Analytic", color=TEAL)
ax.bar(x+0.2, mc, 0.36, yerr=mc_err, capsize=4, label="Monte Carlo (mean ± SD, 10 seeds)", color=GOLD)
ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_title("Analytic vs. Monte Carlo (coastal, 5 m, 20 NTU, night)")
ax.legend(frameon=False); ax.grid(axis="y", ls=":", alpha=.4)
fig.tight_layout(); fig.savefig(f"{FIG}/fig7_mc.png", dpi=200); plt.close(fig)

# ---------- 9) Misalignment sweep at coastal 10 m, NTU 25
mis_rows = []
for phi in (0.0, 0.5, 1.0, 2.0, 5.0, 10.0):
    ci2 = base_ci(distance_m=10.0, ntu=25.0, misalignment_mrad=phi)
    ch2 = evaluate_channel(ci2); ev2 = evaluate_qkd(ch2, cfg)
    lm2 = max_secure_distance(ci2, cfg)
    mis_rows.append({"phi_mrad": phi, "eta_mis": ch2["eta_mis"], "mis_db": ch2["mis_loss_db"],
                     "R_kbps": ev2["secure_rate_bps"]/1e3, "qber": ev2["qber_percent"],
                     "status": ev2["security_status"], "lmax": lm2})
OUT["misalign"] = mis_rows

# ---------- 10) Optimal mu at baseline
opt_mu, opt_r = optimal_mu(ci, cfg)
OUT["opt_mu"] = {"mu_star": opt_mu, "bits_per_pulse": opt_r, "kbps": opt_r*1e7/1e3}

# ---------- 11) Secret fraction figure
fig = fig_secret_fraction(); fig.savefig(f"{FIG}/fig8_secret_fraction.png", dpi=200); plt.close(fig)

# ---------- optimal k completeness check
OUT["env"] = {"python": sys.version.split()[0], "numpy": np.__version__,
              "datetime": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")}

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json"), "w") as f:
    json.dump(OUT, f, indent=2, default=str)
print("\nSaved results.json and figures.")
