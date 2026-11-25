"""Quantum-dot-inspired source model + physics-decomposed intrinsic error
(ported from the AquaSecure digital-twin notebook, with attribution to the
original project source model).

Quasi-single-photon approximation: pulses contain ~one photon with probability
set by source_efficiency; multi-photon probability derived from g²(0).
NOT an experimentally characterised photon source.
"""

from __future__ import annotations
import math


def evaluate_source(mode: str, *, wavelength_nm: float = 532.0,
                    quantum_yield: float = 0.85, rep_rate_hz: float = 1.0e7,
                    linewidth_nm: float = 15.0, g2_zero: float = 0.03,
                    blinking_factor: float = 0.92, temp_c: float = 20.0,
                    filter_bw_nm: float = 10.0) -> dict:
    """Return source metrics. For mode == 'WCP' returns the trivial identity map."""
    if mode == "WCP":
        return {"source_mode": "WCP", "source_efficiency": 1.0,
                "effective_emitted_rate_hz": rep_rate_hz,
                "multi_photon_prob": None, "g2_effective": None,
                "qd_quality_score": None, "spectral_efficiency": 1.0,
                "temp_penalty": 1.0}

    qy = max(0.01, min(1.0, quantum_yield))
    blink = max(0.1, min(1.0, blinking_factor))
    g2 = max(0.0, min(1.0, g2_zero))

    temp_penalty = math.exp(-0.008 * max(0.0, temp_c - 20.0))
    spectral_eff = min(1.0, filter_bw_nm / max(1.0, linewidth_nm * 0.85))
    source_eff = qy * blink * temp_penalty * spectral_eff
    emitted_rate = rep_rate_hz * source_eff
    p_multi = min(0.5, 0.5 * (source_eff ** 2) * g2)
    purity = max(0.0, 1.0 - g2)
    qd_quality = 100.0 * (0.45 * purity + 0.35 * qy + 0.20 * blink) * temp_penalty

    return {"source_mode": "QD", "source_efficiency": source_eff,
            "effective_emitted_rate_hz": emitted_rate,
            "multi_photon_prob": p_multi, "g2_effective": g2,
            "qd_quality_score": qd_quality, "spectral_efficiency": spectral_eff,
            "temp_penalty": temp_penalty}


WATER_DEPOL = {   # depolarisation rate per metre (digital-twin table)
    "Clear ocean": 0.002,
    "Coastal ocean": 0.008,
    "Harbor": 0.020,
    "Turbid harbor": 0.035,
}

TIMING_JITTER_ERROR = 0.004   # 0.4 % base error (digital-twin constant)


def decomposition_errors(pol_error: float, misalign_mrad: float,
                         turbidity_ntu: float, distance_m: float,
                         water_type: str, base_divergence_mrad: float = 5.5) -> dict:
    """Physics-decomposed intrinsic error (digital-twin formulas).

    e_opt = pol_error(nanophotonics) + e_misalign + e_depolarisation + jitter

    Pointing error is converted mrad → deg for the polarisation-rotation term
    (sin² law); note that mrad-scale pointing errors contribute negligibly there,
    which is consistent with pointing appearing mainly as a *coupling* loss.
    """
    mis_deg = misalign_mrad * 1e-3 * (180.0 / math.pi)
    div_sway = 1.0 + 0.45 * max(0.0, (5.5 - base_divergence_mrad) / 5.5) * mis_deg
    e_mis = 0.5 * (math.sin(math.radians(mis_deg * 1.8 * div_sway)) ** 2)
    rate = WATER_DEPOL.get(water_type, 0.008)
    e_dep = 0.5 * (1.0 - math.exp(-rate * (1.0 + 0.02 * turbidity_ntu) * distance_m))
    jitter = TIMING_JITTER_ERROR
    total = min(0.45, pol_error + e_mis + e_dep + jitter)
    return {"pol_error": pol_error, "e_misalign_decomposed": e_mis,
            "e_depolarisation": e_dep, "timing_jitter": jitter,
            "e_intrinsic_decomposed": total}
