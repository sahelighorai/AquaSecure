"""QKD rate and security model for AquaSecure (asymptotic, simplified).

Protocols
---------
* BB84 (simplified, idealised): R = q * Q_mu * [1 - H2(E_mu) - f_ec * H2(E_mu)]
  — the usual asymptotic one-way Shor–Preskill-style expression. It assumes an
  idealised single-photon source and therefore OVERESTIMATES security for weak
  coherent pulses without decoy states. Labelled accordingly in the UI.

* Decoy-state BB84 (simplified vacuum + weak decoy): estimates the
  single-photon yield lower bound Y1^L by eliminating the two-photon term
  (truncation after n=2 photons), then
  R = q * [ Q1^L * (1 - H2(e1^U)) - Q_mu * f_ec * H2(E_mu) ]
  where Q1^L = Y1^L * mu * e^-mu, and e1^U = (E_mu*Q_mu - e0*Y0) / Q1^L
  clipped to [0, 0.5]. Collective attacks, asymptotic limit, one-way error
  correction (error-correction efficiency f_ec >= 1).

Intercept-resend eavesdropping
------------------------------
Eve intercepts a fraction f_eve of pulses, measures in a random basis and
resends. Disturbance added to the *signal* error probability: + 0.25 * f_eve.
Because E_mu (and hence e1^U) absorbs this term, all downstream rates and the
security status respond consistently. This is only ONE attack class; it is not
a general security proof.

Security status thresholds (configurable via module constants)
-------------------------------------------------------------
* QBER >= 11 %            -> Insecure  (above the one-way BB84 threshold)
* Secure-key rate <= 0    -> Insecure
* QBER >= 8 % or R < 1e-4 bits/pulse -> Marginal
* otherwise               -> Secure
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict

QBER_SECURE_MAX = 0.11   # one-way BB84 threshold (asymptotic)
QBER_MARGINAL = 0.08
RATE_MARGINAL_BITS_PER_PULSE = 1.0e-4


def h2(p: float) -> float:
    """Binary entropy in bits."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


@dataclass
class QKDConfig:
    protocol: str = "Decoy-state BB84"       # or "BB84 (ideal source, simplified)"
    mu: float = 0.5                          # mean photon number of signal pulses
    decoy_nu: float = 0.1                    # weak-decoy intensity (decoy mode)
    f_ec: float = 1.16                       # error-correction efficiency
    e_intrinsic: float = 0.015               # intrinsic error (misalignment/optics/detector)
    e0: float = 0.5                          # error rate of background/dark counts
    sift_factor: float = 0.5                 # BB84 basis-sifting factor q
    eve_fraction: float = 0.0                # intercepted fraction (0 = none)
    source_mode: str = "WCP"                 # 'WCP' | 'QD'
    source_eff: float = 1.0                  # QD source efficiency (WCP = 1 identity)
    p_multi: float | None = None             # QD multi-photon probability (g2-derived)
    g2_zero: float | None = None             # QD g2(0)
    qd_quality: float | None = None          # QD quality score / 100
    decomposed_error: bool = False           # opt-in physics-decomposed intrinsic error

    def as_dict(self):
        return asdict(self)


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def gains(mu: float, eta_total: float, y0: float):
    """Total gain and error-gain for intensity mu."""
    q_mu = y0 + 1.0 - math.exp(-eta_total * mu)
    return q_mu


def evaluate_qkd(ch: dict, cfg: QKDConfig) -> dict:
    eta = ch["eta_total"]
    y0 = ch["y0"]
    clock = ch["clock_hz"]
    mu = cfg.mu

    phys_decomp = None
    if cfg.decomposed_error:
        from .source import decomposition_errors
        nano = ch.get("nanophotonic")
        pol = nano["polarization_error_prob"] if nano else 0.0
        phys_decomp = decomposition_errors(
            pol, ch.get("misalignment_mrad", 0.5), ch.get("ntu", 0.0),
            ch.get("distance_m", 0.0), ch.get("water_type", "Coastal ocean"),
            base_divergence_mrad=ch.get("effective_divergence_mrad",
                                        ch.get("divergence_mrad", 5.5)))
        base_e = phys_decomp["e_intrinsic_decomposed"]
    else:
        base_e = cfg.e_intrinsic
    e_d = _clip(base_e + 0.25 * cfg.eve_fraction, 0.0, 0.5)

    q_mu = gains(mu, eta, y0)
    err_mu = e_d * eta * mu + cfg.e0 * y0
    e_mu = err_mu / q_mu if q_mu > 0 else 0.5
    e_mu = _clip(e_mu, 0.0, 0.5)

    received_rate = clock * q_mu                     # detections per second
    sifted_rate = received_rate * cfg.sift_factor    # sifted bits per second
    sifted_bits_per_pulse = q_mu * cfg.sift_factor

    out = {
        "protocol": cfg.protocol,
        "mu": mu,
        "decoy_nu": cfg.decoy_nu,
        "eve_fraction": cfg.eve_fraction,
        "e_d_effective": e_d,
        "e_decomposition": phys_decomp,
        "q_mu": q_mu,
        "e_mu": e_mu,
        "qber_percent": 100.0 * e_mu,
        "received_rate_cps": received_rate,
        "sifted_rate_bps": sifted_rate,
        "sifted_bits_per_pulse": sifted_bits_per_pulse,
        "f_ec": cfg.f_ec,
        "h2_qber": h2(e_mu),
    }

    if cfg.source_mode == "QD":
        # Quasi-single-photon source: Q = Y0 + source_eff * eta (single-photon approx)
        q_sig = cfg.source_eff * eta
        q_mu = y0 + q_sig
        err_mu = e_d * q_sig + cfg.e0 * y0
        e_mu = _clip(err_mu / q_mu if q_mu > 0 else 0.5, 0.0, 0.5)
        h = h2(e_mu)
        p_multi = cfg.p_multi if cfg.p_multi is not None else 0.0
        r_bits_per_pulse = cfg.sift_factor * (
            q_sig * (1.0 - p_multi) * (1.0 - h) - q_mu * cfg.f_ec * h
        )
        out.update({
            "q_mu": q_mu,
            "e_mu": e_mu,
            "qber_percent": 100.0 * e_mu,
            "received_rate_cps": clock * q_mu,
            "sifted_rate_bps": clock * q_mu * cfg.sift_factor,
            "sifted_bits_per_pulse": q_mu * cfg.sift_factor,
            "h2_qber": h,
            "protocol": "QD-BB84 + GLLP (source-aware)",
            "qd_source_eff": cfg.source_eff,
            "qd_p_multi": p_multi,
            "qd_quality": cfg.qd_quality,
            "qd_g2": cfg.g2_zero,
            "e_decomposition": phys_decomp,
        })
        r_bps = r_bits_per_pulse * clock
        out["secure_bits_per_pulse"] = r_bits_per_pulse
        out["secure_rate_bps"] = r_bps
        out["secret_fraction_vs_qber"] = (1.0 - p_multi) * (1.0 - h) - cfg.f_ec * h
        if e_mu >= QBER_SECURE_MAX or r_bits_per_pulse <= 0.0:
            status = "Insecure"
        elif e_mu >= QBER_MARGINAL or r_bits_per_pulse < RATE_MARGINAL_BITS_PER_PULSE:
            status = "Marginal"
        else:
            status = "Secure"
        out["security_status"] = status
        return out

    if cfg.protocol.startswith("Decoy"):
        nu = _clip(cfg.decoy_nu, 1e-3, max(1e-3, mu - 1e-3))   # decoy must be weaker than signal
        q_nu = gains(nu, eta, y0)

        # Two-photon truncated model, vacuum decoy (Y0 from measured vacuum gain)
        denom = mu * math.exp(-mu) * (1.0 - mu / nu)
        term = (mu * mu / (nu * nu)) * math.exp(nu - mu) * (q_nu - y0)
        if abs(denom) < 1e-12:
            y1_l = 0.0
        else:
            y1_l = (q_mu - y0 - term) / denom
        y1_l = _clip(y1_l, 0.0, 1.0)

        q1_l = y1_l * mu * math.exp(-mu)
        if q1_l > 1e-15:
            e1_u = _clip((err_mu - cfg.e0 * y0) / q1_l, 0.0, 0.5)
        else:
            e1_u = 0.5

        r_bits_per_pulse = cfg.sift_factor * (
            q1_l * (1.0 - h2(e1_u)) - q_mu * cfg.f_ec * h2(e_mu)
        )
        out.update({
            "nu": nu,
            "q_nu": q_nu,
            "y1_lower_bound": y1_l,
            "q1_lower_bound": q1_l,
            "e1_upper_bound": e1_u,
            "multiphoton_term_q1": None,
        })
    else:
        r_bits_per_pulse = cfg.sift_factor * q_mu * (
            1.0 - h2(e_mu) - cfg.f_ec * h2(e_mu)
        )

    r_bps = r_bits_per_pulse * clock
    out["secure_bits_per_pulse"] = r_bits_per_pulse
    out["secure_rate_bps"] = r_bps
    out["secret_fraction_vs_qber"] = 1.0 - (1.0 + cfg.f_ec) * h2(e_mu)

    # Security status
    if e_mu >= QBER_SECURE_MAX or r_bits_per_pulse <= 0.0:
        status = "Insecure"
    elif e_mu >= QBER_MARGINAL or r_bits_per_pulse < RATE_MARGINAL_BITS_PER_PULSE:
        status = "Marginal"
    else:
        status = "Secure"
    out["security_status"] = status
    return out


def evaluate_at_distance(ci, cfg: QKDConfig, distance_m: float) -> dict:
    from .channel import evaluate_channel, ChannelInput
    import dataclasses
    ci2 = dataclasses.replace(ci, distance_m=distance_m)
    ch = evaluate_channel(ci2)
    return evaluate_qkd(ch, cfg)


def sweep_distance(ci, cfg: QKDConfig, distances) -> list[dict]:
    return [evaluate_at_distance(ci, cfg, float(d)) | {"distance_m": float(d)} for d in distances]


def max_secure_distance(ci, cfg: QKDConfig, d_min: float = 1.0, d_max: float = 20.0,
                        step: float = 0.1) -> float | None:
    """Largest distance (m) at which QBER < 11 % AND secure-key rate > 0."""
    best = None
    d = d_min
    # Coarse scan then refine locally around the crossing
    last_ok = None
    d = d_min
    while d <= d_max + 1e-9:
        r = evaluate_at_distance(ci, cfg, d)
        if r["qber_percent"] < 100 * QBER_SECURE_MAX and r["secure_bits_per_pulse"] > 0.0:
            last_ok = d
        else:
            if last_ok is not None:
                lo, hi = last_ok, d
                for _ in range(24):
                    mid = 0.5 * (lo + hi)
                    r = evaluate_at_distance(ci, cfg, mid)
                    if r["qber_percent"] < 100 * QBER_SECURE_MAX and r["secure_bits_per_pulse"] > 0.0:
                        lo = mid
                    else:
                        hi = mid
                best = lo
                break
            else:
                return None
        d += step
    else:
        best = last_ok
    return best


def optimal_mu(ci, cfg: QKDConfig, mu_lo: float = 0.05, mu_hi: float = 0.8,
               n: int = 76) -> tuple[float, float]:
    """Grid-search the mu maximising the secure-key rate at the current settings."""
    best_mu, best_r = cfg.mu, -math.inf
    for i in range(n):
        mu = mu_lo + (mu_hi - mu_lo) * i / (n - 1)
        cfg2 = QKDConfig(**{**cfg.as_dict(), "mu": mu})
        r = evaluate_at_distance(ci, cfg2, ci.distance_m)
        if r["secure_bits_per_pulse"] > best_r:
            best_r = r["secure_bits_per_pulse"]
            best_mu = mu
    return best_mu, best_r
