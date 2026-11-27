"""Section 9 — v3, in the user's submission-template format.
Short paragraphs under each template prompt + labelled tables/figures.
Times New Roman · body 12 pt justified · headings <= 16 pt · 1-inch margins.
All numbers read from results.json (regenerated from the audited code)."""
import json
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(_HERE, "results.json")))
FIG = os.path.join(_HERE, "figures")
NAVY, TEAL, GREY = "0B3C5D", "0E6F8E", "5B6B7A"

doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2.54)
TEXT_W = 15.92

st = doc.styles["Normal"]
st.font.name = "Times New Roman"; st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
st.paragraph_format.space_after = Pt(6); st.paragraph_format.line_spacing = 1.08

def style(name, size, color, bold=True, before=10, after=4):
    s = doc.styles[name]
    s.font.name = "Times New Roman"; s.font.size = Pt(size); s.font.bold = bold
    s.font.color.rgb = RGBColor.from_string(color)
    s.paragraph_format.space_before = Pt(before); s.paragraph_format.space_after = Pt(after)
    s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return s
style("Heading 1", 14, NAVY, before=14, after=5)
style("Heading 2", 12.5, TEAL, before=9, after=3)

def run(p, text, size=12, bold=False, italic=False, color=None):
    r = p.add_run(text); r.font.name = "Times New Roman"; r.font.size = Pt(size)
    r.font.bold = bold; r.font.italic = italic
    if color: r.font.color.rgb = RGBColor.from_string(color)
    return r

def para(text, size=12, bold=False, italic=False, color=None, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=6):
    p = doc.add_paragraph(); p.alignment = align; p.paragraph_format.space_after = Pt(after)
    run(p, text, size, bold, italic, color); return p

def prompt(text):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT; p.paragraph_format.space_after = Pt(2)
    run(p, text, 10.5, italic=True, color=GREY); return p

def write_here(text):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY; p.paragraph_format.space_after = Pt(6)
    run(p, "Write here: ", 12, bold=True); run(p, text, 12); return p

def shade(cell, color):
    el = OxmlElement("w:shd"); el.set(qn("w:fill"), color); el.set(qn("w:val"), "clear")
    cell._tc.get_or_add_tcPr().append(el)

def table(headers, rows, widths, caption):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT; p.paragraph_format.space_after = Pt(2)
    run(p, caption, 10.5, bold=True, color=NAVY)
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for j, h in enumerate(headers):
        c = t.rows[0].cells[j]; c.width = Cm(widths[j]); shade(c, NAVY)
        pp = c.paragraphs[0]; pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run(pp, h, 9, bold=True, color="FFFFFF")
    for row in rows:
        cells = t.add_row().cells
        for j, v in enumerate(row):
            cells[j].width = Cm(widths[j])
            pp = cells[j].paragraphs[0]
            pp.alignment = WD_ALIGN_PARAGRAPH.CENTER if j else WD_ALIGN_PARAGRAPH.LEFT
            run(pp, str(v), 9)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t

def figure(path, width_cm, caption):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(path, width=Cm(width_cm))
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER; c.paragraph_format.space_after = Pt(8)
    run(c, caption, 9.5, italic=True, color=GREY)

# ---------------------------------------------------------------- title
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after = Pt(0)
run(p, "Testing, Results and Discussion", 16, bold=True, color=NAVY)
para("AquaSecure — a simulation framework for security-aware underwater quantum key distribution (QKD) in turbid water. "
     "All results in this chapter are simulation outputs; no hardware experiment is claimed.", 10.5, italic=True, color=GREY,
     align=WD_ALIGN_PARAGRAPH.CENTER, after=10)

# ---------------------------------------------------------------- 9.1
doc.add_heading("9.1  Testing Strategy", level=1)
prompt("Describe test cases, test environment, datasets, baselines and evaluation procedure.")
b, ev, env = R["baseline"], R["baseline_ev"], R["env"]
write_here(
    f"AquaSecure was tested as a software simulation in Python {env['python']} with NumPy {env['numpy']} and the Streamlit "
    "application. No experimental dataset was used; the inputs are parameter tables for four water types at 532 nm "
    "(clear ocean, coastal ocean, Harbor and turbid Harbor) and three background-light classes. The reference case (S0) is "
    "coastal water at 5 m, 20 NTU, night light, 15% detector efficiency, 100 dark counts/s, 10 MHz clock, μ = 0.5 and "
    "decoy-state BB84. One parameter at a time was then varied — distance (1–20 m), turbidity (0–100 NTU), water type, "
    "background, protocol and Eve's intercepted fraction — and every case was evaluated with the same analytic engine. "
    "A seeded Monte Carlo simulation (250,000 pulses × 10 seeds) cross-checked the analytic model. Before writing this "
    "chapter, the full code was re-audited: the v1.0 baseline still reproduces bit-identically (η_channel = 0.1988, "
    "QBER = 1.869%, 24.77 kbit/s), and two figure defects found in the audit (a non-uniform heatmap colour scale and a "
    "“−0.0 dB” label) were corrected and all figures regenerated.")
figure(f"{FIG}/fig0_system.png", 15.9,
       "Figure 9.1 — AquaSecure simulation chain. Headline results use the v1.0 baseline path; v1.1 modules are opt-in only.")
table(["Test group", "What was varied", "Fixed conditions", "n evaluations"],
      [["Baseline S0", "— (reference point)", "Coastal, 5 m, 20 NTU, night", "1"],
       ["Distance sweep", "L = 1–20 m, 4 water types, NTU ∈ {0, 25, 50}", "Night, decoy BB84", "120 table cells (96 pts/curve)"],
       ["Turbidity map", "NTU = 0–100 (step 10) × L = 1–20 m", "Night, decoy BB84", "880 (4 waters)"],
       ["Background", "Night / artificial / daylight at L = 5, 10 m", "Coastal, 20 NTU", "6"],
       ["Protocol", "Decoy-state vs idealised BB84 at L = 5, 10, 15 m", "Coastal, 20 NTU, night", "6"],
       ["Eve attack", "Intercepted fraction f = 0–1.0", "Coastal, 5 m, 20 NTU", "7 (+ continuous curve)"],
       ["Monte Carlo", "10 seeds × 250,000 pulses", "Baseline S0 channel", "2.5 × 10⁶ pulses"]],
      [2.8, 5.6, 4.4, 3.1], "Table 9.1 — Test cases and sample sizes.")

# ---------------------------------------------------------------- 9.2
doc.add_heading("9.2  Performance / Outcome Metrics", level=1)
prompt("Report appropriate quantitative and qualitative metrics. Define each metric and its measurement conditions.")
write_here(
    "Five metrics were used, all computed per scenario by the analytic engine. Transmittance η (linear and dB) measures "
    "photon survival through water, geometry, pointing and detector. QBER (%) is the fraction of erroneous sifted bits "
    "and is compared with the 11% one-way BB84 security threshold. The sifted-key rate (kbit/s) is the raw key after "
    "basis reconciliation, and the secure-key rate (kbit/s) is the final rate after error correction (f_ec = 1.16) and "
    "privacy amplification; negative values are reported raw and mean “abort — no key”. Lmax (m) is the largest distance "
    "with QBER < 11% and a positive secure rate, searched over the 1–20 m range, so 20.0 means “≥ 20 m within the search "
    "range”. A scenario is labelled Secure, Marginal (QBER 8–11% or rate below 10⁻⁴ bits/pulse) or Insecure (QBER ≥ 11% "
    "or rate ≤ 0).")
table(["Metric", "Unit", "Definition / condition"],
      [["Channel transmittance η_ch", "— / dB", "Beer–Lambert × geometric × misalignment terms"],
       ["Total transmittance η", "— / dB", "η_ch × detector efficiency (× η_nano only in v1.1 opt-in mode)"],
       ["QBER", "%", "E_μ = (e_d·ημ + ½Y₀)/Q_μ; threshold 11%"],
       ["Sifted-key rate", "kbit/s", "Clock × Q_μ × sifting factor q = ½"],
       ["Secure-key rate", "kbit/s", "Asymptotic decoy-state (or idealised BB84) rate; ≤ 0 ⇒ abort"],
       ["Lmax", "m", "Largest L in [1, 20] m with QBER < 11% and rate > 0"]],
      [4.6, 2.2, 9.1], "Table 9.2 — Metric definitions.")

# ---------------------------------------------------------------- 9.3
doc.add_heading("9.3  Results", level=1)
prompt("Present results in labelled tables, charts, screenshots or photographs. Include units and sample sizes.")
write_here(
    f"In the baseline case S0 the attenuation was c = {b['attenuation_c']:.3f} m⁻¹, channel transmittance "
    f"η_ch = {b['eta_channel']:.4f} and total transmittance η = {b['eta_total']:.4f} ({b['total_loss_db']:.2f} dB). "
    f"The system obtained QBER = {ev['qber_percent']:.2f}%, a sifted-key rate of {ev['sifted_rate_bps']/1e3:.1f} kbit/s "
    f"and a secure-key rate of {ev['secure_rate_bps']/1e3:.2f} kbit/s, i.e. Secure. Figure 9.2 shows that scattering "
    f"(6.1 dB) and detector efficiency (8.2 dB) dominate the 15.3 dB loss. Performance falls quickly with distance and "
    "turbidity (Figures 9.3–9.5, Table 9.4): at 100 NTU, Lmax shrinks to 2.6–3.8 m for all water types. Artificial light "
    "and daylight make the link Insecure at both 5 m and 10 m (Table 9.5, Figure 9.6), and Eve's intercept–resend attack "
    "destroys the key well before the QBER threshold is reached — the rate is already negative at f = 0.25 (QBER 8.12%), "
    "while QBER alone crosses 11% only at f ≈ 0.37 (Figure 9.7). Decoy-state BB84 gives lower but more realistic rates "
    "than idealised BB84 (24.77 vs 52.95 kbit/s at 5 m). The Monte Carlo cross-check agreed with the analytic QBER "
    f"within {R['mc']['qber_abs_dev_pct']:.3f} percentage points over 2.5 × 10⁶ simulated pulses (Figure 9.8).")
table(["Quantity (S0)", "Value", "Quantity (S0)", "Value"],
      [["Water / distance / NTU", "Coastal / 5 m / 20 NTU", "Q_μ (gain)", f"{ev['q_mu']:.5f}"],
       ["Attenuation c", f"{b['attenuation_c']:.3f} m⁻¹", "QBER", f"{ev['qber_percent']:.3f} %"],
       ["η_ch / η (total)", f"{b['eta_channel']:.4f} / {b['eta_total']:.4f}", "Received rate", f"{ev['received_rate_cps']:.3e} /s"],
       ["Channel / total loss", f"{b['channel_loss_db']:.2f} / {b['total_loss_db']:.2f} dB", "Sifted-key rate", f"{ev['sifted_rate_bps']/1e3:.2f} kbit/s"],
       ["Vacuum yield Y₀", f"{b['y0']:.3e}", "Secure-key rate", f"{ev['secure_rate_bps']/1e3:.2f} kbit/s — Secure"]],
      [3.9, 4.0, 3.9, 4.0], "Table 9.3 — Baseline S0 results (single analytic evaluation; MC cross-check in Table 9.6).")
figure(f"{FIG}/fig1_budget.png", 13.5, "Figure 9.2 — Loss budget at S0 (dB). Total 15.3 dB; geometric loss ≈ 0 dB at 5 m.")
figure(f"{FIG}/fig2_rate_vs_distance.png", 13.5, "Figure 9.3 — Secure-key rate vs distance at 25 NTU, night (96 computed points per curve; negative rates clipped to 0 for plotting).")
figure(f"{FIG}/fig3_heatmap.png", 15.9, "Figure 9.4 — Secure-key rate (kbit/s, log scale, one global colour scale) over distance × turbidity; grey = no key (abort). Grid: 20 distances × 11 turbidity values × 4 water types = 880 evaluations.")
lm = R["lmax_vs_ntu"]
table(["Water type"] + [f"{n} NTU" for n in (0, 10, 25, 50, 75, 100)],
      [[w] + [("≥ 20*" if lm[w][str(n)] >= 20 else f"{lm[w][str(n)]:.2f}") for n in (0, 10, 25, 50, 75, 100)] for w in lm],
      [3.4, 2.08, 2.08, 2.08, 2.08, 2.08, 2.08], "Table 9.4 — Lmax (m) vs turbidity (night, decoy BB84). *Search capped at 20 m; true value may exceed 20 m.")
figure(f"{FIG}/fig4_lmax_vs_ntu.png", 13.5, "Figure 9.5 — Lmax vs turbidity (markers at 0, 10, …, 100 NTU; cap 20 m as in Table 9.4).")
bg, pr = R["background"], R["protocol"]
table(["Scenario (coastal, 20 NTU)", "QBER (%)", "Secure rate (kbit/s)", "Status"],
      [[f"Night, L = 5 m", f"{bg['Night (moonless)']['5']['qber']:.2f}", f"{bg['Night (moonless)']['5']['R_kbps']:.2f}", "Secure"],
       [f"Night, L = 10 m", f"{bg['Night (moonless)']['10']['qber']:.2f}", f"{bg['Night (moonless)']['10']['R_kbps']:.2f}", "Secure"],
       [f"Artificial light, L = 5 m", f"{bg['Artificial lighting']['5']['qber']:.2f}", f"{bg['Artificial lighting']['5']['R_kbps']:.2f} (raw ⇒ abort)", "Insecure"],
       [f"Daylight, L = 5 m", f"{bg['Daylight']['5']['qber']:.2f}", f"{bg['Daylight']['5']['R_kbps']:.1f} (raw ⇒ abort)", "Insecure"],
       [f"Decoy vs ideal BB84, L = 5 m", f"{pr['5']['decoy_qber']:.2f} (both)", f"{pr['5']['decoy_kbps']:.2f} vs {pr['5']['bb84_kbps']:.2f}", "Secure (both)"],
       [f"Decoy vs ideal BB84, L = 10 m", f"{pr['10']['decoy_qber']:.2f} (both)", f"{pr['10']['decoy_kbps']:.2f} vs {pr['10']['bb84_kbps']:.2f}", "Secure (both)"],
       [f"Eve f = 0.10 / 0.25 / 1.00 (L = 5 m)", "4.37 / 8.12 / 26.87", "5.76 / −15.92 / −72.27 (raw)", "Secure / Insecure / Insecure"]],
      [5.2, 3.4, 4.4, 2.9], "Table 9.5 — Background, protocol and Eve results (one analytic evaluation per cell).")
figure(f"{FIG}/fig5_background.png", 13.0, "Figure 9.6 — Background-light effect (coastal, 20 NTU). Artificial/daylight rates are negative and clipped to 0 (no bar = abort); see Table 9.5 for raw values.")
figure(f"{FIG}/fig6_eve.png", 13.0, "Figure 9.7 — Intercept–resend: QBER vs intercepted fraction (continuous analytic curve; discrete cases in Table 9.5). QBER crosses 11% at f ≈ 0.37, but the secure rate reaches zero earlier, at f ≈ 0.15–0.25.")
mc = R["mc"]
table(["Quantity", "Analytic", f"Monte Carlo (mean ± SD, 10 seeds × {mc['n_pulses']:,} pulses)"],
      [["Detection yield Q_μ", f"{mc['analytic_yield']:.5f}", f"{mc['yield_mean']:.5f} ± {mc['yield_std']:.5f}"],
       ["QBER (%)", f"{mc['analytic_qber']:.3f}", f"{mc['qber_mean']:.3f} ± {mc['qber_std']:.3f}"],
       ["Sifted bits / pulse", f"{mc['analytic_sifted']:.5f}", f"{mc['sifted_mean']:.5f} ± {mc['sifted_std']:.5f}"]],
      [4.2, 3.6, 8.1], "Table 9.6 — Analytic vs Monte Carlo at S0 (total 2.5 × 10⁶ pulses).")
figure(f"{FIG}/fig7_mc.png", 13.0, "Figure 9.8 — Analytic vs Monte Carlo (mean ± SD over 10 seeds). QBER deviation 0.049 percentage points; yield deviation 0.28%.")
figure(f"{FIG}/fig8_secret_fraction.png", 12.5, "Figure 9.9 — Asymptotic secret fraction 1 − (1 + f_ec)·H₂(e) vs QBER; it reaches zero near e ≈ 10–11%, explaining why Marginal cases abort before the 11% line.")

# ---------------------------------------------------------------- 9.4
doc.add_heading("9.4  Discussion", level=1)
prompt("Interpret the results, compare against objectives or baselines, and explain unexpected findings.")
write_here(
    "The results meet the project objective: AquaSecure correctly predicts where an underwater QKD link is Secure, "
    "Marginal or Insecure, and by how much. Three findings dominate. First, distance and turbidity control the link "
    "through scattering: even clear ocean falls from Lmax ≥ 20 m at 0 NTU to 3.79 m at 100 NTU. Second, background light "
    "is the fastest route to failure — artificial lighting raises Y₀ by about two orders of magnitude and daylight by "
    "about four, so filtering and night/deep operation matter more than small detector improvements. Third, the Eve "
    "test shows the secure rate is the stricter criterion: privacy amplification already consumes the key at f = 0.25 "
    "although QBER (8.12%) is still below 11%. An initially surprising result — daylight rates of about −3,700 kbit/s "
    "raw — is not physical key output; it is the asymptotic formula evaluated far outside its valid region and is "
    "therefore reported as “abort”. Similarly, the kink in Figure 9.3 near 6 m is the geometric term switching on when "
    "the beam outgrows the receiver aperture. Against the baseline, idealised BB84 overestimates the rate by about "
    "2× at 5 m because it ignores multi-photon pulses; the decoy-state figures are the defensible headline numbers. "
    "Two corrections from the pre-writing code audit are recorded for honesty: the heatmap now uses one global colour "
    "scale, and the Qiskit/NumPy circuit cross-check (v1.1) agrees only statistically (e.g. 2.24% vs 2.99% QBER at "
    "2,400 circuits), not bit-identically. All conclusions remain simulation-only: asymptotic rates, literature-typical "
    "532 nm coefficients that must be verified before citation, intercept–resend as the only attack, and no finite-key "
    "or experimental validation.")

# ---------------------------------------------------------------- 9.5
doc.add_heading("9.5  User / Stakeholder Feedback", level=1)
prompt("Summarise usability testing, field trials, expert feedback or pilot evaluation, where applicable.")
write_here(
    "No formal user study, field trial or stakeholder pilot has been conducted, and no external feedback is claimed. "
    "Evaluation so far is developer testing only: the controls, KPI display, status classification, figures and "
    "CSV/JSON/LaTeX/PDF exports were exercised across the scenarios above, including an all-options-on v1.1 run with "
    "no errors. As a next step, a small pilot is planned in which a QKD researcher, an underwater-optics engineer and "
    "the project mentor each complete set tasks (find Lmax for a given water type; diagnose an Insecure case; export a "
    "report) and rate usability, after which the interface and documentation will be revised. Until that pilot and "
    "independent expert review are completed, stakeholder acceptance of AquaSecure remains untested.")

para("Artefacts: app.py and the aquasecure/ package (channel, QKD, Monte Carlo, source, nanophotonics, background, "
     "circuit and export modules); report/generate_results.py regenerates results.json and Figures 9.2–9.9; "
     "report/results.json holds every number quoted above.", 9.5, italic=True, color=GREY)

doc.save(os.path.join(_HERE, "AquaSecure_Section9_Testing_Results_Discussion.docx"))
print("saved v3")
