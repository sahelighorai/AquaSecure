"""Nanophotonic transmitter structures (ported from the AquaSecure digital-twin
notebook, ported here with attribution to the original project source model).

Structure lookup table — analytic, literature-inspired values for:
  eta_ext_base     base extraction efficiency
  div_factor       beam-divergence multiplier (< 1 = better collimation)
  directionality   directionality gain
  align_tol_deg    alignment tolerance (degrees)
  per_db           polarization extinction ratio (dB)
  immersion_loss   coupling loss into water (fraction)

These are engineering approximations, NOT fabricated-device measurements.
"""

from __future__ import annotations
import math

NANOPHOTONIC_STRUCTURES = {
    "None": {"eta_ext_base": 0.18, "div_factor": 1.00, "directionality": 1.0,
             "align_tol_deg": 1.2, "per_db": 18.0, "immersion_loss": 0.22},
    "Dielectric metasurface": {"eta_ext_base": 0.78, "div_factor": 0.28, "directionality": 4.2,
                               "align_tol_deg": 2.8, "per_db": 28.0, "immersion_loss": 0.06},
    "Plasmonic antenna": {"eta_ext_base": 0.62, "div_factor": 0.45, "directionality": 2.8,
                          "align_tol_deg": 2.2, "per_db": 22.0, "immersion_loss": 0.14},
    "Nanowire": {"eta_ext_base": 0.72, "div_factor": 0.35, "directionality": 3.5,
                 "align_tol_deg": 2.5, "per_db": 26.0, "immersion_loss": 0.08},
}


def evaluate_nanophotonic(structure: str, user_eta_ext: float | None,
                          base_divergence_mrad: float) -> dict:
    specs = NANOPHOTONIC_STRUCTURES.get(structure, NANOPHOTONIC_STRUCTURES["None"])
    eta_ext = user_eta_ext if user_eta_ext is not None else specs["eta_ext_base"]
    eta_ext = max(0.10, min(0.90, eta_ext))
    base_div = max(1.0, min(20.0, base_divergence_mrad))

    effective_div = max(0.5, base_div * specs["div_factor"])
    water_coupling = 1.0 - specs["immersion_loss"]
    net_tx_efficiency = eta_ext * water_coupling
    per_linear = 10.0 ** (specs["per_db"] / 10.0)
    pol_error = 1.0 / (1.0 + per_linear)

    return {
        "structure_type": structure,
        "extraction_efficiency": eta_ext,
        "effective_divergence_mrad": effective_div,
        "directionality_gain": specs["directionality"],
        "alignment_tolerance_deg": specs["align_tol_deg"],
        "polarization_error_prob": pol_error,
        "water_coupling_efficiency": water_coupling,
        "net_tx_efficiency": net_tx_efficiency,
    }
