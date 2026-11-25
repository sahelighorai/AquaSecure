"""Vectorised Monte Carlo BB84 simulation (NumPy).

Purpose: independent stochastic cross-check of the analytic model, in the
spirit of the AquaSecure NumPy vs. limited Qiskit Aer comparison described in
the research-gap document — this is a software-level cross-check, not
experimental validation.

Model per pulse
---------------
n            ~ Poisson(mu)                    (photons emitted)
click_sig    with prob 1 - (1 - eta_total)**n (signal detection)
click_noise  with prob Y0                     (dark + background)
click        = click_sig OR click_noise
sifted       = click AND (random basis match, prob 1/2)
error        : signal clicks err with prob e_d_eff (incl. Eve),
               pure-noise clicks err with prob 0.5

Eve (intercept-resend, fraction f_eve): each intercepted pulse is measured in
a random basis and resent; adds 0.25 to the signal error probability
(e_d_eff = e_intrinsic + 0.25 * f_eve), consistent with the analytic model.
"""

from __future__ import annotations

import numpy as np


def run_bb84_mc(n_pulses: int, mu: float, eta_total: float, y0: float,
                e_d_effective: float, eve_fraction: float,
                seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)

    n = rng.poisson(mu, n_pulses)
    p_click = 1.0 - np.power(1.0 - eta_total, n)
    click_sig = rng.random(n_pulses) < p_click
    click_noise = rng.random(n_pulses) < y0
    click = click_sig | click_noise

    sifted = click & (rng.random(n_pulses) < 0.5)
    n_sifted = int(sifted.sum())

    err_prob = np.where(click_sig, e_d_effective, 0.5)
    errors = (rng.random(n_pulses) < err_prob) & sifted
    n_errors = int(errors.sum())

    detections = int(click.sum())
    qber = (n_errors / n_sifted) if n_sifted > 0 else float("nan")

    return {
        "n_pulses": n_pulses,
        "seed": seed,
        "detections": detections,
        "detection_yield": detections / n_pulses,
        "sifted_bits": n_sifted,
        "sifted_fraction": n_sifted / n_pulses,
        "errors": n_errors,
        "qber": qber,
        "qber_percent": 100.0 * qber if np.isfinite(qber) else float("nan"),
        "eve_fraction": eve_fraction,
        # Standard error of the QBER sample (binomial)
        "qber_stderr": (qber * (1 - qber) / n_sifted) ** 0.5 if n_sifted > 0 else float("nan"),
    }
