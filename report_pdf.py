"""One-page PDF report of the current scenario (ReportLab)."""

from __future__ import annotations
import datetime

def build_pdf(snap: dict, recommendations: list[dict], figure_paths: list[str] | None = None) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, Image as RLImage)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    import io

    # Register a Unicode serif (Greek glyphs: η, μ, λ, π) when available; else Times
    import os
    font_name, bold_name = "Times-Roman", "Times-Bold"
    REG = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
    REGB = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
    if os.path.exists(REG) and os.path.exists(REGB):
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        pdfmetrics.registerFont(TTFont("AquaSerif", REG))
        pdfmetrics.registerFont(TTFont("AquaSerif-Bold", REGB))
        font_name, bold_name = "AquaSerif", "AquaSerif-Bold"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.6*cm, rightMargin=1.6*cm,
                            topMargin=1.4*cm, bottomMargin=1.4*cm,
                            title="AquaSecure Simulation Report")
    styles = getSampleStyleSheet()
    navy = colors.HexColor("#0B3C5D"); teal = colors.HexColor("#0E6F8E")
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontName=bold_name,
                        fontSize=19, textColor=navy, spaceAfter=2)
    small = ParagraphStyle("small", parent=styles["Normal"], fontName=font_name,
                           fontSize=8, textColor=colors.HexColor("#5B6B7A"))
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], fontName=bold_name,
                        fontSize=12, textColor=teal, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName=font_name,
                          fontSize=9.5, leading=13)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=10, spaceAfter=2)

    status = str(snap.get("security_status", "?")).upper()
    status_color = {"SECURE": "#0f7b5f", "MARGINAL": "#d97706", "INSECURE": "#b91c1c"}.get(status, "#5b6b7a")

    story = [
        Paragraph("AquaSecure — Underwater QKD Simulation Report", h1),
        Paragraph(f"Generated {datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')} · "
                  f"Version 1.1 · Simulation-only, not hardware-validated", small),
        Spacer(1, 6),
        Paragraph(f'<font color="{status_color}"><b>Security status: {status}</b></font> &nbsp;&nbsp;'
                  f'QBER {snap["qber_percent"]:.2f} % · Secure rate {max(snap["secure_rate_bps"],0)/1e3:.2f} kbit/s · '
                  + (f'L<sub>max</sub> {snap["max_secure_distance_m"]:.2f} m' if snap["max_secure_distance_m"] is not None else "L<sub>max</sub> &lt; 1 m"),
                  body),
        Spacer(1, 8),
    ]

    def table(rows, widths, header=True):
        t = Table(rows, colWidths=widths)
        style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d6de")),
                 ("FONTNAME", (0, 0), (-1, -1), font_name),
                 ("FONTSIZE", (0, 0), (-1, -1), 8),
                 ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1),
                  [colors.white, colors.HexColor("#f2f8fa")])]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), navy),
                      ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                      ("FONTNAME", (0, 0), (-1, 0), bold_name)]
        t.setStyle(TableStyle(style))
        return t

    story.append(Paragraph("Scenario", h3))
    story.append(table([
        ["Parameter", "Value", "Parameter", "Value"],
        ["Water type", str(snap["water_type"]), "Wavelength", f"{snap.get('wavelength_nm', 532):.0f} nm"],
        ["Distance", f"{snap['distance_m']:.1f} m", "Turbidity", f"{snap['ntu']:.0f} NTU"],
        ["Background", str(snap["background"]) if snap.get("background_model", "preset") == "preset"
            else f"{snap.get('background_physics_level')} (physics, {snap.get('filter_bw_nm', 10):.0f} nm, {snap.get('receiver_fov_mrad', 50):.0f} mrad)"],
        ["Protocol", str(snap["protocol"]), "μ", f"{snap['mu']:.2f}"],
        ["Source", str(snap.get("source_mode", "WCP")), "Nanophotonics", str(snap.get("nanophotonic_structure", "None"))],
        ["Detector eff.", f"{100 * snap['detector_efficiency']:.0f} %", "Dark counts", f"{snap['dark_count_cps']:.0f} cps"],
        ["Eve", f"{100 * snap['eve_fraction']:.0f} % intercepted", "Misalignment", f"{snap['misalignment_mrad']:.1f} mrad"],
    ], [4.2*cm, 4.6*cm, 4.0*cm, 4.6*cm]))

    story.append(Paragraph("Key results", h3))
    story.append(table([
        ["Metric", "Value"],
        ["Channel transmittance η_ch", f"{snap['eta_channel']:.3e}  ({snap['channel_loss_db']:.1f} dB)"],
        ["Total transmittance η (incl. detector)", f"{snap['eta_total']:.3e}  ({snap['total_loss_db']:.1f} dB)"],
        ["Attenuation c", f"{snap['attenuation_c_m^-1']:.3f} m^-1"],
        ["Received photon rate", f"{snap['received_rate_cps']:.3e} /s"],
        ["QBER", f"{snap['qber_percent']:.2f} %"],
        ["Sifted-key rate", f"{snap['sifted_rate_bps']/1e3:.2f} kbit/s"],
        ["Secure-key rate", f"{max(snap['secure_rate_bps'], 0.0)/1e3:.2f} kbit/s  ({snap['secure_bits_per_pulse']:.2e} bits/pulse)"],
        ["Maximum secure distance", f"{snap['max_secure_distance_m']:.2f} m" if snap['max_secure_distance_m'] is not None else "< 1 m"],
    ], [8.0*cm, 9.4*cm]))

    story.append(Paragraph("Recommended operating settings", h3))
    for r_ in recommendations[:6]:
        story.append(Paragraph(f"<b>[{r_['priority'].upper()}] {r_['area']}.</b> {r_['action']}", bullet))

    if figure_paths:
        story.append(Paragraph("Diagnostic figures", h3))
        for fp in figure_paths:
            try:
                story.append(RLImage(fp, width=15.5*cm, height=8.6*cm, kind="proportional"))
                story.append(Spacer(1, 4))
            except Exception:
                pass

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<i>Claim boundary: asymptotic, collective-attack, one-way security. No finite-key composability; "
        "intercept–resend is the only modelled attack; turbulence excluded from the baseline verdict; "
        "water coefficients are literature-typical and not site-calibrated. 'Secure' denotes a positive "
        "asymptotic secret-key rate with QBER below the configured threshold under this model.</i>", small))
    doc.build(story)
    return buf.getvalue()
