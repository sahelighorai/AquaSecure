"""Rule-based 'recommended operating settings' engine.

Explainable IF–THEN rules (the AquaSecure AdaptiveControlEngine baseline from
the research-gap document). NOT a globally optimal controller; GA/PSO/BO are
identified there as future comparison baselines.
"""

from __future__ import annotations


def build_recommendations(ch: dict, ev: dict, cfg, opt_mu: float,
                          l_max: float | None) -> list[dict]:
    recs: list[dict] = []

    def add(priority, area, finding, action, expected):
        recs.append({"priority": priority, "area": area, "finding": finding,
                     "action": action, "expected": expected})

    # --- Distance rule
    if l_max is None:
        add("critical", "Link distance",
            "No secure operating point exists anywhere in 1–20 m for these settings.",
            "Reduce attenuation first (shorter link, lower NTU, larger receiver aperture, better coupling) before attempting key exchange.",
            "Restores a positive secure-key rate once QBER < 11 % and R > 0.")
    elif ch["distance_m"] > l_max:
        add("critical", "Link distance",
            f"Current distance {ch['distance_m']:.1f} m exceeds the secure limit ({l_max:.2f} m).",
            f"Operate at ≤ {l_max:.2f} m, or improve the link budget.",
            "Returns the link to the Secure region.")
    else:
        margin = l_max - ch["distance_m"]
        if margin < 2.0:
            add("high", "Link distance",
                f"Only {margin:.2f} m of secure margin remains (max ≈ {l_max:.2f} m).",
                "Keep the link comfortably below the limit; small turbidity or pointing excursions can break security.",
                "Robust Secure operation with headroom.")
        else:
            add("info", "Link distance",
                f"{margin:.1f} m of secure margin (max ≈ {l_max:.2f} m).",
                "Current distance is comfortable; no change required.",
                "Maintains Secure status.")

    # --- Eavesdropper
    if cfg.eve_fraction > 0:
        add("critical", "Eavesdropper",
            f"Intercept-resend active on {100 * cfg.eve_fraction:.0f} % of pulses (adds ≈ {25 * cfg.eve_fraction:.1f} % QBER).",
            "Abort the session; discard sifted bits. Investigate the link. Re-run with Eve disabled only after the link is cleared.",
            "Prevents disclosure of key material to Eve.")

    # --- Turbidity / scattering dominance
    if ch["scattering_ntu_b"] > ch["absorption_a"] and ch["scattering_ntu_b"] > ch["scattering_base_b"]:
        add("high", "Water condition",
            f"NTU-driven scattering ({ch['scattering_ntu_b']:.2f} m⁻¹) dominates the loss budget.",
            "Operate at lower-NTU times/locations, shorten the link, or use a narrower FOV receiver to reject scattered background light.",
            "Lowers c directly; every 1 m⁻¹ reduction ≈ 1 dB/m saved.")
    elif ch["attenuation_c"] > 1.0:
        add("medium", "Water condition",
            f"High total attenuation c = {ch['attenuation_c']:.2f} m⁻¹.",
            "Prefer the clearest water available; consider 450–490 nm (blue) for clear ocean.",
            "Reduces Beer–Lambert loss.")

    # --- Background-light limited
    bg_y0 = ch["bg_photons_per_gate"]
    dc_y0 = ch["dark_counts_per_gate"]
    if bg_y0 > 5 * dc_y0:
        add("high", "Background light",
            f"Background ({ch['background_cps']:.0e} cps, {bg_y0:.2e} photons/gate) dominates noise.",
            "Tighten spatial (FOV), spectral (band-pass < 20 nm) and temporal (ns gating) filtering; prefer night or shielded operation.",
            "Lower Y0 → lower QBER → higher secure rate.")
    # --- Dark-count limited
    elif dc_y0 > bg_y0:
        add("medium", "Detector",
            f"Dark counts ({ch['dark_count_cps']:.0f} cps) dominate the noise budget.",
            "Cool the detector, use gated operation, raise the detection threshold, or lower the clock rate.",
            "Lower Y0; especially valuable at long distance where signal is faint.")

    # --- Alignment
    if ch["eta_mis"] < 0.8:
        add("high", "Pointing & alignment",
            f"Misalignment costs {ch['mis_loss_db']:.1f} dB (transverse offset {1e3 * ch['misalign_disp_m']:.1f} mm at the receiver).",
            "Reduce pointing error below ~0.2 mrad (active steering / beacon / faster tracking).",
            "Recovers dB directly in the link budget.")

    if ch["eta_geo"] < 0.3:
        add("medium", "Receiver aperture",
            f"Geometric coupling captures only {100 * ch['eta_geo']:.1f} % of the beam.",
            "Enlarge the receiver aperture or reduce beam divergence.",
            "Geometric loss falls quadratically with aperture/beam-ratio.")

    # --- Protocol choice
    if not cfg.protocol.startswith("Decoy"):
        add("high", "Protocol",
            "Idealised BB84 assumes a single-photon source; weak coherent pulses leak information (PNS attack).",
            "Switch to Decoy-state BB84 for any realistic source.",
            "Closes the photon-number-splitting vulnerability at a modest rate cost.")

    # --- Intensity
    if abs(opt_mu - cfg.mu) > 0.05:
        direction = "increase" if opt_mu > cfg.mu else "reduce"
        add("medium", "Signal intensity",
            f"Current μ = {cfg.mu:.2f}; grid search optimum ≈ μ = {opt_mu:.2f}.",
            f"{direction.capitalize()} μ toward {opt_mu:.2f}.",
            "Maximises the secure-key rate at fixed distance.")

    # --- QBER watch
    if 0.08 <= ev["e_mu"] < 0.11:
        add("high", "QBER",
            f"QBER {ev['qber_percent']:.2f} % is in the 8–11 % caution band.",
            "Check alignment, background and polarisation drift; reduce μ; verify with a longer test transmission.",
            "Pulls QBER back below the 8 % comfort line.")

    # --- Wavelength / scattering regime
    if ch.get("wavelength_nm", 532.0) < 515.0 and ch["ntu"] > 10.0:
        add("medium", "Wavelength",
            f"Operating at {ch['wavelength_nm']:.0f} nm in {ch['ntu']:.0f} NTU water.",
            "Shift toward 515–525 nm; scattering falls with λ (≈ λ^-1.14 Mie regime). Absorption is not re-modelled here — treat as indicative.",
            "Lower b(λ) lowers c; helpful but secondary to turbidity reduction.")

    # --- Nanophotonic transmitter
    if ch.get("nanophotonic_structure", "None") == "None" and ch["eta_geo"] < 0.5:
        add("medium", "Transmitter optics",
            f"Geometric capture is {100 * ch['eta_geo']:.0f} % without beam shaping.",
            "Consider a dielectric metasurface (divergence ×0.28 → capture grows quadratically) with extraction efficiency ≥ 0.65.",
            "Large coupling gain; see Sweeps → transmitter benchmark.")

    # --- QD source quality
    qd_q = ev.get("qd_quality")
    if qd_q is not None and qd_q < 70.0:
        add("medium", "Source quality",
            f"QD quality score {qd_q:.0f}/100 (yield/blinking/g² below target).",
            "Raise quantum yield/blinking, cool the emitter, or narrow the emission below the filter window.",
            "Higher source efficiency with lower multi-photon probability.")

    # --- Physics-based background: filtering knobs
    if ch.get("background_model") == "physics" and ch.get("filter_bw_nm", 10.0) > 5.0:
        add("high", "Spectral filtering",
            f"Physics-based background with {ch['filter_bw_nm']:.0f} nm bandwidth and {ch['receiver_fov_mrad']:.0f} mrad FOV.",
            "Tighten to ≤ 5 nm band-pass and ≤ 30 mrad FOV; background scales linearly with both.",
            "Often the single largest win against noise (see §9.3.5 of the report).")

    # --- All good
    if ev["security_status"] == "Secure" and not cfg.eve_fraction:
        add("info", "Status",
            f"Secure at {ev['secure_rate_bps'] / 1e3:.1f} kbit/s ({1000 * ev['secure_bits_per_pulse']:.2f} secret bits per 1000 pulses).",
            "Optional: raise the clock rate (if the APD/Spad timing allows) or increase μ toward the optimum.",
            "Higher throughput with identical security margin.")

    priority_rank = {"critical": 0, "high": 1, "medium": 2, "info": 3}
    recs.sort(key=lambda r: priority_rank[r["priority"]])
    return recs
