"""Underwater optical channel model for AquaSecure.

v1.1 extension: optional wavelength scaling (default 532 nm reproduces v1.0
bit-identically), opt-in nanophotonic transmitter stage, and an optional
physics-based background model.

Components
----------
1. Modified Beer–Lambert:
     c = a + b(λ) + k·NTU·f(λ),  b(λ) = b₅₃₂·(532/λ)^1.14,  f(λ) = (532/λ)^0.8
     η_BL = 10^(−cL/10)
   Absorption a is kept at its green-window table value (a(λ) not modelled).
2. Geometric spreading: w(L) = w₀ + L·tan(θ_eff/2); η_geo = min(1, (r_rx/w)²)
   where θ_eff = base divergence × structure div_factor (nanophotonic, opt-in).
3. Pointing/misalignment: η_mis = exp(−2(L·tan φ / w)²)
4. Nanophotonic stage (opt-in): η_nano = η_extraction · (1 − immersion_loss);
   also contributes pol_error (auditable; feeds the decomposed-error model).
5. Background (two modes):
   - preset   (default, v1.0): fixed detector cps per lighting class; per-gate
     yield = cps / clock_hz; dark counts likewise.
   - physics  : flux × rx_area × FOV² × bandwidth × exp(−a·min(L,5)); per-gate
     yield = cps × gate_window.
   Decomposing absorption a of background self-shielding uses the table a.

Turbulence remains an optional overlay (Sweeps tab), not part of the baseline verdict.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict

from .waters import WATER_TYPES, BACKGROUND_LEVELS
from .background import background_cps_physics

WAVELENGTH_REF_NM = 532.0


@dataclass
class ChannelInput:
    water_type: str = "Coastal ocean"
    distance_m: float = 5.0
    ntu: float = 20.0
    k_ntu: float = 0.05
    background: str = "Night (moonless)"
    detector_efficiency: float = 0.15
    dark_count_cps: float = 100.0
    clock_hz: float = 1.0e7
    misalignment_mrad: float = 0.5
    divergence_mrad: float = 10.0
    tx_aperture_radius_m: float = 0.02
    rx_aperture_radius_m: float = 0.05
    wavelength_nm: float = 532.0
    background_model: str = "preset"            # 'preset' | 'physics'
    background_physics_level: str = "Low ambient"
    filter_bw_nm: float = 10.0
    gate_window_ns: float = 1.0
    receiver_fov_mrad: float = 50.0
    nanophotonic_structure: str = "None"        # 'None' | structure name
    nanophotonic_eta_ext: float | None = None   # None -> structure default


def beam_radius(w0_m: float, distance_m: float, divergence_full_rad: float) -> float:
    return w0_m + distance_m * math.tan(divergence_full_rad / 2.0)


def _nano_stage(ci: ChannelInput):
    """Compute the nanophotonic stage once, or return None when inactive."""
    if ci.nanophotonic_structure == "None":
        return None
    from .nanophotonics import evaluate_nanophotonic
    return evaluate_nanophotonic(ci.nanophotonic_structure,
                                 ci.nanophotonic_eta_ext,
                                 ci.divergence_mrad)


def evaluate_channel(ci: ChannelInput) -> dict:
    a = WATER_TYPES[ci.water_type]["absorption"]
    b_532 = WATER_TYPES[ci.water_type]["scattering"]

    wl = ci.wavelength_nm
    wl_b = (WAVELENGTH_REF_NM / wl) ** 1.14
    wl_n = (WAVELENGTH_REF_NM / wl) ** 0.8
    b_lambda = b_532 * wl_b
    ntu_lambda = ci.k_ntu * ci.ntu * wl_n
    c = a + b_lambda + ntu_lambda

    beer_loss_db = c * ci.distance_m
    eta_beer = 10.0 ** (-beer_loss_db / 10.0)

    nano = _nano_stage(ci)
    div_mrad = nano["effective_divergence_mrad"] if nano else ci.divergence_mrad

    w = beam_radius(ci.tx_aperture_radius_m, ci.distance_m, div_mrad * 1e-3)
    eta_geo = min(1.0, (ci.rx_aperture_radius_m / w) ** 2)
    geo_loss_db = -10.0 * math.log10(max(eta_geo, 1e-12))

    d = ci.distance_m * math.tan(ci.misalignment_mrad * 1e-3)
    eta_mis = math.exp(-2.0 * (d / w) ** 2)
    mis_loss_db = -10.0 * math.log10(max(eta_mis, 1e-12))

    eta_nano = nano["net_tx_efficiency"] if nano else 1.0
    nano_loss_db = -10.0 * math.log10(max(eta_nano, 1e-12)) if nano else 0.0

    eta_channel = eta_beer * eta_geo * eta_mis
    eta_total = eta_channel * eta_nano * ci.detector_efficiency
    channel_db = -10.0 * math.log10(max(eta_channel * eta_nano, 1e-12))
    total_db = -10.0 * math.log10(max(eta_total, 1e-12))

    if ci.background_model == "physics":
        r_bg = background_cps_physics(ci.background_physics_level,
                                      ci.rx_aperture_radius_m,
                                      ci.receiver_fov_mrad * 1e-3,
                                      ci.filter_bw_nm, a, ci.distance_m)
        gate_s = ci.gate_window_ns * 1e-9
        n_bg = r_bg * gate_s
        n_dc = ci.dark_count_cps * gate_s
    else:
        r_bg = BACKGROUND_LEVELS[ci.background]
        n_bg = r_bg / ci.clock_hz
        n_dc = ci.dark_count_cps / ci.clock_hz
    y0 = 1.0 - math.exp(-(n_bg + n_dc))

    return {
        **asdict(ci),
        "absorption_a": a,
        "scattering_base_b": b_532,
        "scattering_lambda_b": b_lambda,
        "scattering_ntu_b": ntu_lambda,
        "attenuation_c": c,
        "wavelength_factor_b": wl_b,
        "beer_loss_db": beer_loss_db,
        "beer_loss_absorption_db": a * ci.distance_m,
        "beer_loss_scattering_db": (b_lambda + ntu_lambda) * ci.distance_m,
        "eta_beer": eta_beer,
        "beam_radius_m": w,
        "effective_divergence_mrad": div_mrad,
        "eta_geo": eta_geo,
        "geo_loss_db": geo_loss_db,
        "misalign_disp_m": d,
        "eta_mis": eta_mis,
        "mis_loss_db": mis_loss_db,
        "eta_nano": eta_nano,
        "nano_loss_db": nano_loss_db,
        "eta_channel": eta_channel,
        "eta_total": eta_total,
        "channel_loss_db": channel_db,
        "total_loss_db": total_db,
        "bg_photons_per_gate": n_bg,
        "dark_counts_per_gate": n_dc,
        "y0": y0,
        "background_cps": r_bg,
        "nanophotonic": nano,
    }


def eta_beer_only(ci: ChannelInput) -> float:
    a = WATER_TYPES[ci.water_type]["absorption"]
    b_lambda = WATER_TYPES[ci.water_type]["scattering"] * (WAVELENGTH_REF_NM / ci.wavelength_nm) ** 1.14
    ntu_lambda = ci.k_ntu * ci.ntu * (WAVELENGTH_REF_NM / ci.wavelength_nm) ** 0.8
    return 10.0 ** (-(a + b_lambda + ntu_lambda) * ci.distance_m / 10.0)
