"""Physics-based background-light model (ported from the AquaSecure
digital-twin notebook), as an opt-in alternative to the fixed cps presets.

Receiver-side background detection rate:

  bg_cps = flux[level]                (photons / s / m² / sr / nm)
         × rx_area = π r_rx²          (m²)
         × solid_angle = π FOV²       (sr)
         × filter_bw                  (nm)
         × exp(−a·min(L, 5 m))        (self-shielding of the water column)

Defaults (gate = 1 ns): Night 1e6, Low ambient 5e8, Artificial 2.5e10,
Daylight 5e12 ph/s/m²/sr/nm. Per-gate yield = bg_cps × gate_window_s.

These are order-of-magnitude engineering values; users calibrating a real
receiver must measure radiance for their site and filter stack.
"""

from __future__ import annotations
import math

BACKGROUND_FLUX = {
    "Night": 1.0e6,
    "Low ambient": 5.0e8,
    "Artificial lighting": 2.5e10,
    "Daylight": 5.0e12,
}


def background_cps_physics(level: str, rx_aperture_radius_m: float,
                           fov_rad: float, filter_bw_nm: float,
                           absorption_a: float, distance_m: float) -> float:
    flux = BACKGROUND_FLUX[level]
    rx_area = math.pi * rx_aperture_radius_m ** 2
    solid_angle = math.pi * fov_rad ** 2
    return flux * rx_area * solid_angle * filter_bw_nm * math.exp(
        -absorption_a * min(distance_m, 5.0))
