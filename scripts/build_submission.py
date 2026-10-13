"""Build the hackathon submission documents as designed PDFs (docs/pdf/):

    DawaDrishti_Solution_Document.pdf   the full story: problem (the guide's six steps), finding, solution, evidence
    DawaDrishti_Solution_Brief.pdf      the same in two pages
    DawaDrishti_Presentation.pdf        a 16:9 deck for the final presentation

Every number is read from artifacts/ (written by `python -m dawadrishti build`), so the documents cannot drift from
the code. Screenshots come from docs/submission/img/.

    pip install playwright && python -m playwright install chromium
    python scripts/build_submission.py
"""
from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts"
IMG = ROOT / "docs" / "submission" / "img"
OUT = ROOT / "docs" / "pdf"
LIVE = "https://dawadrishti.onrender.com"
REPO = "https://github.com/AbhishekJadli007/dawadrishti"

A = lambda n: json.loads((ART / f"{n}.json").read_text())
STUDY, ER, AUDIT, RISK, NET, BPI, XCHK = (A("memory_study"), A("entity_resolution"), A("extraction_audit"), A("risk"),
                                         A("network_effect"), A("bpi2019_conformance"), A("conformance_crosscheck"))
EX = json.loads((ROOT / "docs" / "submission" / "examples.json").read_text())
H = STUDY["headline"]
FT = RISK["factory"]["test"]
CONF = FT["confound"]
BT = RISK["batch"]["test"]
ERT = {m["matcher"]: m for m in ER["matchers"]}
pct = lambda x, d=1: f"{100 * x:.{d}f}%"
n = lambda x: f"{int(round(x)):,}"


def img(name: str) -> str:
    return "data:image/jpeg;base64," + base64.b64encode((IMG / f"{name}.jpg").read_bytes()).decode()


SOURCES = [
    ("CDSCO NSQ alerts: public portal and monthly PDFs", "https://cdscoonline.gov.in/CDSCO/Drugs"),
    ("Lok Sabha via IndiaMedToday: 3,104 of 1.16 lakh samples NSQ in 2024–25", "https://indiamedtoday.com/over-3000-drug-samples-declared-not-of-standard-quality-in-2024-25-nadda/"),
    ("IANS: 211 samples flagged NSQ in October 2025", "https://ianslive.in/cdsco-labs-flag-211-drug-samples-as-not-of-standard-quality-in-october--20251121110525"),
    ("ETV Bharat, 15 Oct 2025: Coldrif death toll reaches 24", "https://www.etvbharat.com/en/bharat/madhya-pradesh-coldrif-cough-syrup-fatality-count-rises-after-many-children-die-enn25101506375"),
    ("The South First: WHO alert, syrups linked to 66 child deaths in The Gambia", "https://thesouthfirst.com/health/who-issues-alert-as-syrups-manufactured-by-indian-firm-are-linked-to-deaths-of-66-children-in-gambia"),
    ("Down To Earth: 40 failed samples from one supplier in Rajasthan", "https://www.downtoearth.org.in/amp/story/health/cough-syrup-deaths-in-rajasthan-families-allege-negligence-while-government-denies-link-to-medicine"),
    ("Deccan Herald: Rajasthan halts Kaysons distribution, suspends drug controller", "https://www.deccanherald.com/amp/story/india%2Frajasthan%2Fcough-syrup-row-rajasthan-government-suspends-drug-controller-halts-distribution-of-kaysons-pharma-drugs-3752117"),
    ("DT Next: CDSCO starts risk-based inspection in 6 states", "https://www.dtnext.in/amp/story/news/national/cough-syrup-deaths-cdsco-starts-risk-based-inspection-at-manufacturing-units-in-6-states-848582"),
    ("BPI Challenge 2019 (van Dongen, 4TU.ResearchData)", "https://icpmconference.org/2019/?p=302"),
]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&family=JetBrains+Mono:wght@500&display=swap');
:root { --teal:#0d9488; --indigo:#4f46e5; --rose:#e11d48; --amber:#d97706; --ink:#0f172a; --muted:#526077; --faint:#8a96a8; --line:#e3e8ef; --bg:#f6f8fb; --soft:#f1f5f9; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { font-family: Inter, sans-serif; color: var(--ink); -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.d { font-family: 'Plus Jakarta Sans', Inter, sans-serif; letter-spacing: -0.02em; }
.mono { font-family: 'JetBrains Mono', monospace; }
.muted { color: var(--muted); } .faint { color: var(--faint); } .teal { color: var(--teal); } .rose { color: var(--rose); } .indigo { color: var(--indigo); }
.grad { background: linear-gradient(92deg, var(--teal), var(--indigo)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.grad-alert { background: linear-gradient(92deg, #e11d48, #f97316); -webkit-background-clip: text; background-clip: text; color: transparent; }
.eyebrow { font-size: 10px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: var(--teal); }
.card { background: #fff; border: 1px solid var(--line); border-radius: 14px; box-shadow: 0 8px 24px -16px rgba(15,23,42,.25); }
.pill { display: inline-block; border-radius: 999px; padding: 3px 10px; font-size: 10px; font-weight: 700; border: 1px solid; }
.pill.teal { background:#f0fdfa; border-color:#99f6e4; color:#0f766e } .pill.rose { background:#fff1f2; border-color:#fecdd3; color:#be123c }
.pill.amber { background:#fffbeb; border-color:#fde68a; color:#92400e } .pill.indigo { background:#eef2ff; border-color:#c7d2fe; color:#4338ca }
table { width: 100%; border-collapse: collapse; font-size: 10.5px; }
th { text-align: left; font-weight: 600; color: var(--muted); padding: 5px 6px; border-bottom: 1px solid var(--line); }
td { padding: 5px 6px; border-bottom: 1px solid #eef2f7; vertical-align: top; }
td.r, th.r { text-align: right; } tr.hl td { background: #f0fdfa; font-weight: 600; }
.shot { width: 100%; border-radius: 12px; border: 1px solid var(--line); box-shadow: 0 16px 40px -24px rgba(15,23,42,.45); display: block; }
.bar { height: 9px; border-radius: 99px; background: var(--soft); overflow: hidden; } .bar > i { display: block; height: 100%; border-radius: 99px; }
a { color: var(--teal); text-decoration: none; }
.quote { border-left: 4px solid var(--rose); background: #fff1f2; padding: 10px 14px; border-radius: 0 12px 12px 0; font-weight: 600; color: #4c0519; line-height: 1.5; }
.callout { background: linear-gradient(135deg, #f0fdfa, #eef2ff); border: 1px solid #c7f2ea; border-radius: 14px; padding: 12px 14px; }
.chip { display:inline-block; border:1px solid var(--line); background:#fff; border-radius:999px; padding:4px 10px; margin:3px; }
"""

DOC_CSS = CSS + """
@page { size: A4; margin: 0; }
.page { width: 210mm; height: 297mm; padding: 16mm 16mm 14mm; position: relative; overflow: hidden; page-break-after: always; background: #fff; }
.page:last-child { page-break-after: auto; }
.page h2 { font-size: 25px; font-weight: 800; margin: 4px 0 10px; }
.page h3 { font-size: 15px; font-weight: 700; margin: 14px 0 5px; }
.page p, .page li { font-size: 12px; line-height: 1.6; color: #253047; }
.page table { font-size: 11.3px; } .page td, .page th { padding: 6px 7px; }
.page ul { padding-left: 16px; } .page li { margin: 2px 0; }
.foot { position: absolute; left: 16mm; right: 16mm; bottom: 8mm; display: flex; justify-content: space-between; font-size: 8.5px; color: var(--faint); border-top: 1px solid var(--line); padding-top: 5px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; } .grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; } .grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.stat .v { font-family: 'Plus Jakarta Sans'; font-weight: 800; font-size: 27px; letter-spacing: -0.02em; } .stat .l { font-size: 10.5px; color: var(--muted); line-height: 1.35; margin-top: 2px; }
.box { padding: 12px 14px; } .step { display:flex; gap:10px; align-items:flex-start; margin: 7px 0; }
.num { flex: none; width: 22px; height: 22px; border-radius: 50%; background: #f0fdfa; color: var(--teal); font-weight: 800; font-size: 11px; display:flex; align-items:center; justify-content:center; border: 1px solid #99f6e4; }
.page .quote { font-size: 13px; }
"""

DECK_CSS = CSS + """
@page { size: 1280px 720px; margin: 0; }
.slide { width: 1280px; height: 720px; padding: 56px 72px; position: relative; overflow: hidden; page-break-after: always; background: #fff; }
.slide:last-child { page-break-after: auto; }
.slide h1 { font-size: 46px; font-weight: 800; line-height: 1.08; } .slide h2 { font-size: 36px; font-weight: 800; line-height: 1.1; margin: 8px 0 18px; }
.slide p, .slide li { font-size: 19px; line-height: 1.5; color: #253047; } .slide ul { padding-left: 22px; } .slide li { margin: 6px 0; }
.sn { position: absolute; right: 40px; bottom: 26px; font-size: 13px; color: var(--faint); } .brand { position: absolute; left: 72px; bottom: 26px; font-size: 13px; color: var(--faint); display:flex; gap:8px; align-items:center; }
.big { font-family: 'Plus Jakarta Sans'; font-weight: 800; letter-spacing: -0.03em; }
table { font-size: 16px; } th, td { padding: 9px 10px; }
"""


def ring(value: float, size: int = 180, stroke: int = 16, color: str = "#e11d48", label: str = "", fs: float = 0.2) -> str:
    r = (size - stroke) / 2
    c = 2 * 3.14159265 * r
    return f"""<div style="position:relative;width:{size}px;height:{size}px">
      <svg width="{size}" height="{size}" style="transform:rotate(-90deg)"><circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="#f1f5f9" stroke-width="{stroke}"/>
      <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-dasharray="{c}" stroke-dashoffset="{c * (1 - value)}"/></svg>
      <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center">
        <div class="d" style="font-weight:800;font-size:{size * fs}px">{pct(value)}</div><div style="font-size:{max(9, size * 0.055)}px;color:#526077;padding:0 {size*0.16}px;line-height:1.3">{label}</div></div></div>"""


def bars(rows: list[tuple[str, float, str, str]], label_w: str = "42%") -> str:
    out = ""
    for lab, v, color, txt in rows:
        out += f"""<div style="display:flex;align-items:center;gap:8px;margin:6px 0"><div style="width:{label_w};font-size:10.5px">{lab}</div>
          <div class="bar" style="flex:1"><i style="width:{100*v:.1f}%;background:{color}"></i></div><div style="width:46px;text-align:right;font-size:10.5px;font-weight:700">{txt}</div></div>"""
    return out


LOGO = """<svg width="{s}" height="{s}" viewBox="0 0 64 64"><defs><linearGradient id="lg{s}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d9488"/><stop offset="1" stop-color="#4f46e5"/></linearGradient></defs>
<rect width="64" height="64" rx="18" fill="url(#lg{s})"/><path d="M11 32c5.5-9.5 12.5-14.5 21-14.5S47.5 22.5 53 32c-5.5 9.5-12.5 14.5-21 14.5S16.5 41.5 11 32z" fill="#fff"/>
<circle cx="32" cy="32" r="8.5" fill="#0d9488"/><circle cx="32" cy="32" r="3.4" fill="#fff"/></svg>"""
logo = lambda s=28: LOGO.replace("{s}", str(s))

PROBLEM_SENTENCE = ("Public medicine buyers in India (state medical-services corporations, hospitals, the Jan Aushadhi scheme) "
                    "cannot see a supplier's national quality record before they buy, because CDSCO's failure alerts are scattered "
                    "across monthly PDFs and a portal, the same factory is spelled hundreds of ways, and nothing connects them to "
                    "buyers' purchasing systems. As a result, repeat failures reach patients: "
                    f"{pct(H['repeat_share'])} of failed batches come from factories already on the national list.")
SOLUTION_SENTENCE = ("DawaDrishti turns nine years of CDSCO alerts into one national quality memory, with a lookup that any "
                     "buyer's ERP can call at purchase order and at goods receipt. It returns the factory's public record and a "
                     "graded answer on what to do now, and every claim is tested against a baseline.")


def foot(i: int, total: int) -> str:
    return f'<div class="foot"><span>DawaDrishti · Solution document · COMMIT FOR GOOD 2026</span><span>{i} / {total}</span></div>'


def supply_chain(big: bool = False) -> str:
    f = 1.5 if big else 1
    stages = [("Make", "factory produces a batch", "#e2e8f0"), ("Test", "state & central labs sample it", "#e2e8f0"),
              ("Alert", "CDSCO publishes failures", "#fecdd3"), ("Buy", "buyer's ERP raises a PO", "#fde68a"),
              ("Store", "warehouse quarantines", "#e2e8f0"), ("Use", "hospital gives it to a patient", "#e2e8f0")]
    cells = ""
    for i, (s, d, c) in enumerate(stages):
        cells += f"""<div style="flex:1;text-align:center"><div style="margin:0 auto;width:{46*f}px;height:{46*f}px;border-radius:50%;background:{c};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:{13*f}px" class="d">{i+1}</div>
          <div style="font-weight:700;font-size:{12*f}px;margin-top:{5*f}px">{s}</div><div style="font-size:{9*f}px;color:#526077;line-height:1.3;padding:0 4px">{d}</div></div>"""
        if i < len(stages) - 1:
            cells += f'<div style="padding-top:{18*f}px;color:#cbd5e1;font-size:{18*f}px">→</div>'
    gap = f"""<div style="position:relative;margin:{10*f}px 0 0;height:{30*f}px"><div style="position:absolute;left:38%;width:16%;top:0;height:{26*f}px;border:2px dashed #e11d48;border-top:none;border-radius:0 0 14px 14px"></div>
      <div style="position:absolute;left:24%;right:24%;top:{30*f}px;text-align:center;font-size:{10.5*f}px;font-weight:700;color:#be123c">The break: an alert never reaches the next buyer's purchase order</div></div>"""
    return f'<div style="display:flex;align-items:flex-start">{cells}</div>{gap}'


def architecture(scale: float = 1) -> str:
    def b(t, s, c="#fff", bc="#e3e8ef"):
        return f'<div style="flex:1;background:{c};border:1.5px solid {bc};border-radius:12px;padding:{8*scale}px {9*scale}px;text-align:center"><div style="font-weight:700;font-size:{11.5*scale}px">{t}</div><div style="font-size:{9*scale}px;color:#526077;line-height:1.3;margin-top:2px">{s}</div></div>'
    arrow = f'<div style="align-self:center;color:#94a3b8;font-size:{18*scale}px;padding:0 {3*scale}px">→</div>'
    row1 = "".join([b("CDSCO alerts", "portal JSON + monthly PDFs", "#fff1f2", "#fecdd3"), arrow,
                    b("Extraction + audit", "parse, clean, check vs portal"), arrow,
                    b("Entity resolution", "5,521 names → factories, review queue", "#eef2ff", "#c7d2fe"), arrow,
                    b("Warehouse", "DuckDB star schema"), arrow,
                    b("Lookup API", "record + graded response", "#f0fdfa", "#99f6e4"), arrow,
                    b("Buyer ERPs", "PO and goods receipt", "#fffbeb", "#fde68a")])
    row2 = "".join([b("Headline study", "repeat share, bootstrap CI"), b("Conformance engine", "declarative rules; BPI 2019"),
                    b("Patterns", "FP-Growth, clusters, spikes"), b("Attention model", "gradient boosting vs baselines"),
                    b("Questions", "LLM picks a reviewed query template")])
    return f'<div style="display:flex;align-items:stretch">{row1}</div><div style="text-align:center;color:#94a3b8;font-size:{11*scale}px;margin:{6*scale}px 0">▼ analysis on the same warehouse ▼</div><div style="display:flex;gap:{8*scale}px">{row2}</div>'


def eval_rows() -> list[tuple[str, str, str, str]]:
    m = FT["results"]
    return [
        ("Failed batches from factories already on record", "Real", pct(H["repeat_share"]), f"95% CI {pct(H['repeat_share_ci95'][0])}–{pct(H['repeat_share_ci95'][1])}; exact names would show {pct(STUDY['ablation']['exact string']['repeat_share'])}"),
        ("PDF reader vs CDSCO portal", "Real", pct(AUDIT["row_precision"]), f"rows matched; fields agree {pct(min(v['agreement'] for v in AUDIT['fields'].values()))}–{pct(max(v['agreement'] for v in AUDIT['fields'].values()))}"),
        ("Name matching, held-out hard pairs", "Real", f"P {ERT['Fuzzy ≥92, v2 rules']['test']['firm']['precision']:.2f} / R {ERT['Fuzzy ≥92, v2 rules']['test']['firm']['recall']:.2f}", f"exact names R 0.00; earlier rules R {ERT['Fuzzy ≥92, v1 rules (before fixes)']['test']['firm']['recall']:.2f}; with review R {ER['with_human_review']['recall_if_reviewers_confirm']['test']['firm']['recall']:.2f}"),
        ("Who appears in the next 6 months of alerts", "Real", f"AUC {m['Attention model (ML)']['auc']:.3f}", f"best simple rule {m['Most past failures']['auc']:.3f}; top-50: simple rule wins ({pct(m['Most recent failure']['top50']['precision'],0)} vs {pct(m['Attention model (ML)']['top50']['precision'],0)})"),
        ("Same, when a new lab finds the failure", "Real", f"AUC {CONF['detected_elsewhere'][0]['model_auc']:.3f}", f"{CONF['detected_elsewhere'][0]['units']} of {FT['positives']} units; state-only model {CONF['state_only_baseline_auc']:.3f}"),
        ("Conformance engine on a real SAP log", "Real", f"{n(BPI['rules'][0]['violating_cases'])}", f"payments before goods receipt in {n(BPI['events'])} events; published counts reproduced exactly"),
        ("Test the riskiest batch first", "Simulated", pct(BT["results"]["DawaDrishti risk order"]["caught_in_first_30pct"]), f"of failures caught in first 30% of tests vs {pct(BT['results']['First in, first out']['caught_in_first_30pct'])} first-in-first-out"),
        ("Shared memory vs isolated ERPs", "Simulated", f"−{100*(1-NET['network']['orders_to_debarred']/NET['isolated']['orders_to_debarred']):.0f}%", f"orders to debarred suppliers; failed batches received −{100*(1-NET['network']['failed_batches']/NET['isolated']['failed_batches']):.0f}%"),
    ]


def example_json() -> str:
    """The real lookup response, one top-level key per line so it reads at a glance."""
    ex = EX["lookup_example"]
    lines = [f'  "{k}": {json.dumps(v, ensure_ascii=False)}' for k, v in ex.items()]
    return ("{\n" + ",\n".join(lines) + "\n}").replace("<", "&lt;")


# =====================================================================================================  solution document
def solution_document() -> str:
    pages = []
    T = 12
    cases = STUDY["worked_cases"]
    # 1 cover
    pages.append(f"""<div class="page" style="padding:0;background:linear-gradient(160deg,#f0fdfa 0%,#ffffff 45%,#eef2ff 100%)">
      <div style="padding:18mm 16mm 0">
        <div style="display:flex;align-items:center;gap:10px">{logo(40)}<div><div class="d" style="font-weight:800;font-size:20px">DawaDrishti</div><div style="font-size:10px;color:#526077">दवा दृष्टि · India's medicine-quality memory</div></div></div>
        <div class="eyebrow" style="margin-top:26mm">Solution document · COMMIT FOR GOOD 2026 · AI for Resilient and Sustainable Supply Chains</div>
        <h1 class="d" style="font-size:42px;line-height:1.05;font-weight:800;margin-top:10px">Most failed medicines come from factories <span class="grad-alert">we already knew about.</span></h1>
        <p style="font-size:14px;line-height:1.6;color:#3b4760;margin-top:14px;max-width:150mm">{SOLUTION_SENTENCE}</p>
        <div style="display:flex;gap:22px;align-items:center;margin-top:14mm">
          {ring(H['repeat_share'], 200, 18, label='of failed batches came from a factory already on the national list')}
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;flex:1">
            <div class="card box stat"><div class="v">{n(STUDY['data']['records_used'])}</div><div class="l">failed batches studied, Sep 2017 – Aug 2026 (real CDSCO alerts)</div></div>
            <div class="card box stat"><div class="v">{H['median_months_first_to_next']:.0f} months</div><div class="l">typical gap between a factory's first failure and its next</div></div>
            <div class="card box stat"><div class="v">{pct(H['repeat_detected_by_new_lab'],0)}</div><div class="l">of repeats found by a lab that had never caught that factory</div></div>
            <div class="card box stat"><div class="v">{pct(STUDY['ablation']['exact string']['repeat_share'])}</div><div class="l">what you'd see with exact names. Name matching is the whole game.</div></div>
          </div>
        </div>
      </div>
      <img src="{img('home_hero')}" style="position:absolute;left:16mm;right:16mm;bottom:30mm;width:178mm;border-radius:12px;border:1px solid #e3e8ef;box-shadow:0 20px 50px -25px rgba(15,23,42,.5)">
      <div style="position:absolute;left:16mm;right:16mm;bottom:12mm;display:flex;justify-content:space-between;font-size:10px;color:#526077">
        <span><b>Live:</b> <a href="{LIVE}">{LIVE.replace('https://','')}</a> &nbsp;·&nbsp; <b>Code:</b> <a href="{REPO}">{REPO.replace('https://','')}</a> (MIT)</span><span>Abhishek Jadli · October 2026</span></div>
    </div>""")
    # 2 executive summary
    pages.append(f"""<div class="page"><div class="eyebrow">In one page</div><h2 class="d">Executive summary</h2>
      <div class="quote">{PROBLEM_SENTENCE}</div>
      <div class="grid2" style="margin-top:12px">
        <div class="card box"><div class="eyebrow" style="color:#e11d48">The problem</div><p style="margin-top:4px">India declared <b>3,104</b> drug samples not of standard quality in 2024–25. The worst cases kill:
          <b>24 children</b> had died after taking Coldrif cough syrup by 15 October 2025. CDSCO publishes every failure, but as monthly PDFs and a portal no buyer's system reads.
          A supplier that fails in one state can keep winning orders in another.</p></div>
        <div class="card box"><div class="eyebrow" style="color:#4f46e5">What we found</div><p style="margin-top:4px">We joined nine years of alerts by factory. <b>{pct(H['repeat_share'])}</b> of failed batches
          (95% CI {pct(H['repeat_share_ci95'][0])}–{pct(H['repeat_share_ci95'][1])}) came from a factory that already had an alert in an earlier month, usually about {H['median_months_first_to_next']:.0f} months earlier, and
          half the time found by a different lab or state. A buyer checking the record would have seen it.</p></div>
        <div class="card box"><div class="eyebrow">What we built</div><p style="margin-top:4px">A <b>national quality memory</b> and a <b>lookup API</b> any ERP can call at purchase order and goods receipt.
          The public view shows the published record only. The buyer view adds a graded response (pause / test every batch / prefer alternatives). A reference buyer console shows it in use:
          an order is warned, and a batch already on the national failure list is held on arrival.</p></div>
        <div class="card box"><div class="eyebrow" style="color:#d97706">How we know it works</div><p style="margin-top:4px">
          <b>Data:</b> the PDF reader agrees with CDSCO's portal on {pct(AUDIT['row_precision'])} of rows.<br>
          <b>Names:</b> name matching made no false merges on held-out pairs.<br>
          <b>Prediction:</b> the model beats the best simple rule on AUC ({FT['results']['Attention model (ML)']['auc']:.3f} vs {FT['results']['Most past failures']['auc']:.3f}), and we report where the rule wins.<br>
          <b>Process checks:</b> the same engine reproduces the published counts of a 1.6M-event SAP log.</p></div>
      </div>
      <h3 style="margin-top:14px">Try it in two minutes</h3>
      <div class="grid3" style="margin-top:6px">
        <div class="card box"><div class="num">1</div><p style="margin-top:6px">Open <a href="{LIVE}">{LIVE.replace('https://','')}</a>. Let it wake up (about 1 minute, free hosting).</p></div>
        <div class="card box"><div class="num">2</div><p style="margin-top:6px"><b>Check a manufacturer</b> → "Nestor Pharmaceuticals" → switch to <b>Buyer view</b>.</p></div>
        <div class="card box"><div class="num">3</div><p style="margin-top:6px"><b>For buyers</b> → "Use the demo order" → order from Scott-Edil → use the red batch chip → watch it get held.</p></div>
      </div>
      <h3>Which AI capabilities, and why</h3>
      <table style="font-size:10.3px"><tr><th>Capability (from the brief)</th><th>In DawaDrishti</th><th>Why this method</th></tr>
        <tr><td><b>Explain</b></td><td>Entity resolution and the national record per factory</td><td>Fuzzy matching with a human review queue: transparent, testable, no black box over named firms</td></tr>
        <tr><td><b>Detect</b></td><td>Exact-batch check at goods receipt; conformance rules on event logs</td><td>Deterministic rules where the answer must be certain</td></tr>
        <tr><td><b>Recommend</b></td><td>Graded response with concentration and days of cover</td><td>Simple rules a drug controller can audit, with the supply cost shown beside them</td></tr>
        <tr><td><b>Predict</b></td><td>Future regulatory attention; batch test priority</td><td>Gradient boosting with a time split, always next to baselines</td></tr>
        <tr><td><b>Ask</b></td><td>Plain-English questions → one of nine reviewed query templates</td><td>Gemini only picks a template; it never writes SQL or text about a firm</td></tr>
      </table>
      {foot(2, T)}</div>""")
    # 3 observe + investigate
    pages.append(f"""<div class="page"><div class="eyebrow">Step 1–2 · Observe and investigate</div><h2 class="d">Where the medicine supply chain breaks</h2>
      <p>The participant guide splits a supply chain into source, make, store, move, distribute and use, with information travelling alongside the goods. For public medicines,
      the goods flow works: factories make, buyers order, warehouses store, hospitals dispense. The <b>information flow</b> is what fails. When a government lab finds a bad batch,
      the warning is published, but it does not travel to the next buyer's purchase order.</p>
      <div class="card" style="padding:12px 12px 30px;margin:8px 0">{supply_chain()}</div>
      <h3>Who is affected, and how</h3>
      <div class="grid2">
        <div class="card box"><b>Patients</b><p>Receive medicine that is weak, does not dissolve, is contaminated or fake. In the worst cases, like diethylene glycol in cough syrup, children die.</p></div>
        <div class="card box"><b>Public buyers</b><p>State medical-services corporations, district hospitals and Jan Aushadhi procure through tenders. They test their own stock, but cannot see failures found in other states.</p></div>
        <div class="card box"><b>Regulators</b><p>CDSCO and state drug controllers publish failures and, since October 2025, run risk-based inspections. They need to know where to sample next.</p></div>
        <div class="card box"><b>Honest manufacturers</b><p>Compete on price against firms with repeat failures, and must not be confused with a similarly named firm.</p></div>
      </div>
      <h3>How a failure travels today</h3>
      <div class="step"><div class="num">1</div><p>A state lab in Kerala tests a sample of tablets and finds they do not dissolve. The result goes to CDSCO.</p></div>
      <div class="step"><div class="num">2</div><p>Weeks later it appears in CDSCO's monthly list: one row among about 200, with the maker's name typed by hand.</p></div>
      <div class="step"><div class="num">3</div><p>A corporation in another state opens a tender for the same medicine. Its ERP (DVDMS, e-Aushadhi or its own) checks price and stock, <b>not</b> the national record.
        The same factory wins again. Its next batch fails about {H['median_months_first_to_next']:.0f} months later, found by yet another lab.</p></div>
      <h3>What each group needs, and what DawaDrishti gives them</h3>
      <table style="font-size:10.6px"><tr><th style="width:18%">Who</th><th style="width:38%">Needs</th><th>DawaDrishti gives</th></tr>
        <tr><td><b>Buyer</b></td><td>Know a supplier's record before ordering, in seconds, inside their own system</td><td>One API call at purchase order and goods receipt; a clear "what to do now"</td></tr>
        <tr><td><b>Regulator</b></td><td>Decide where to sample next with limited inspectors</td><td>Units ranked by future regulatory attention, tested against simple rules</td></tr>
        <tr><td><b>Manufacturer</b></td><td>Accuracy, and not being confused with a similarly named firm</td><td>Evaluated name matching, no guessed identities, a correction route</td></tr>
        <tr><td><b>Patient</b></td><td>Medicine that works</td><td>Fewer repeat failures reaching the shelf; a batch on the national list held on arrival</td></tr></table>
      {foot(3, T)}</div>""")
    # 4 quantify + challenge
    pages.append(f"""<div class="page"><div class="eyebrow">Step 3–4 · Quantify and challenge</div><h2 class="d">The evidence, and why existing systems miss it</h2>
      <table style="margin-top:6px"><tr><th style="width:22%">Fact</th><th>Detail</th><th style="width:22%">Source</th></tr>
        <tr><td><b>3,104</b> samples NSQ</td><td>declared not of standard quality in 2024–25, out of 1.16 lakh tested (about 2.7%)</td><td>Lok Sabha via IndiaMedToday</td></tr>
        <tr><td><b>211</b> in one month</td><td>samples flagged NSQ by CDSCO labs in October 2025 alone</td><td>IANS</td></tr>
        <tr><td><b>24</b> children</td><td>had died after taking Coldrif syrup (diethylene glycol), as of 15 October 2025</td><td>ETV Bharat</td></tr>
        <tr><td><b>66</b> children</td><td>deaths in The Gambia linked by WHO to syrups from an Indian manufacturer (2022)</td><td>The South First (WHO alert)</td></tr>
        <tr><td><b>40</b> failed samples</td><td>from one supplier in Rajasthan's state testing (2021–23). It was banned for a year, then reinstated</td><td>Down To Earth; Deccan Herald</td></tr>
        <tr><td><b>{n(STUDY['data']['records_used'])}</b> failed batches</td><td>in CDSCO's own alerts, Sep 2017 – Aug 2026, which we extracted, cleaned and joined (our data)</td><td>CDSCO portal and PDFs</td></tr>
      </table>
      <h3>What already exists, and the gap</h3>
      <table><tr><th style="width:24%">Existing</th><th>What it does</th><th style="width:36%">Where it falls short</th></tr>
        <tr><td><b>CDSCO NSQ alerts</b></td><td>Publishes every failed batch monthly (PDFs since 2017, portal since 2019)</td><td>A list, not a memory: no factory identity, no history per firm, no API, one factory spelled up to 14 ways</td></tr>
        <tr><td><b>DVDMS / e-Aushadhi</b></td><td>Buyers' ERPs: purchase, stock, distribution, quality control</td><td>Never read the national alerts. Each state's failures stay in its own system</td></tr>
        <tr><td><b>Risk-based inspection</b></td><td>CDSCO began targeting factories in 6 states after the 2025 deaths</td><td>Regulator-side only. Says nothing to the buyer about to place an order</td></tr>
        <tr><td><b>Buyers' own testing</b></td><td>Quarantine and test each batch before issue</td><td>Slow labs create pressure to release untested stock, and a buyer's own test can't see failures found elsewhere</td></tr>
      </table>
      <div class="callout" style="margin-top:12px"><b>The gap in one line:</b> the evidence exists and is public, but it is not joined up by factory, not trusted enough to act on, and not available at the moment of purchase.</div>
      <h3>Why this matters for resilience</h3>
      <p>The guide names the recurring failure modes. This problem is three of them at once: <b>information arrives late, incomplete and in incompatible formats</b>; <b>local decisions ignore
      the rest of the network</b>, because a buyer can't see another state's failure; and <b>one supplier can be a single point of failure</b>, so pausing a bad supplier must be weighed against supply.
      DawaDrishti addresses the first two directly, and shows the third (concentration and days of cover) at the moment of decision.</p>
      <h3>Why now</h3>
      <div class="grid3">
        <div class="card box"><b>The data became machine-readable</b><p>CDSCO's portal has carried structured alerts since 2019, alongside the PDFs. For the first time the whole record can be joined.</p></div>
        <div class="card box"><b>The buyers went digital</b><p>States now run DVDMS / e-Aushadhi. There is finally a system to plug the lookup into at the moment of purchase.</p></div>
        <div class="card box"><b>The regulator moved</b><p>After the 2025 deaths, CDSCO started risk-based inspection. The same signal can now reach buyers, not only inspectors.</p></div>
      </div>
      {foot(4, T)}</div>""")
    # 5 define + finding
    abl = STUDY["ablation"]
    pages.append(f"""<div class="page"><div class="eyebrow">Step 5 · Define, and test it with data</div><h2 class="d">The problem in one sentence, and our finding</h2>
      <div class="grid4">
        {''.join(f'<div class="card box"><div class="eyebrow" style="color:{c}">{k}</div><p style="margin-top:3px">{v}</p></div>' for k, v, c in [
          ('Who', 'Public medicine buyers: state medical-services corporations, hospitals, Jan Aushadhi', '#0d9488'),
          ('Cannot', "see a supplier's national quality record before they buy", '#4f46e5'),
          ('Because', 'alerts are scattered PDFs, one factory has many spellings, and nothing reaches their ERP', '#d97706'),
          ('Which causes', f"repeat failures to reach patients: {pct(H['repeat_share'])} of failed batches come from factories already listed", '#e11d48')])}
      </div>
      <div style="display:flex;gap:18px;margin-top:14px;align-items:center">
        {ring(H['repeat_share'], 170, 16, label='already on record')}
        <div style="flex:1"><h3 style="margin-top:0">What we measured</h3><p>For every failed batch we asked: had the same factory appeared in an alert in an <b>earlier month</b>? Measured on {n(STUDY['data']['records_used'])} batches
          from {n(H['firms'])} factories. The 95% confidence interval ({pct(H['repeat_share_ci95'][0])}–{pct(H['repeat_share_ci95'][1])}) comes from resampling factories 1,000 times.
          Among critical failures (contamination, sterility, adulteration, fakes) the share is {pct(H['repeat_share_critical'])}.</p></div></div>
      <div class="grid4" style="margin-top:12px">
        <div class="card box stat"><div class="v">{H['median_months_first_to_next']:.0f} mo</div><div class="l">median gap from first failure to the next</div></div>
        <div class="card box stat"><div class="v">{pct(H['repeat_detected_by_new_lab'],0)}</div><div class="l">of repeats found by a lab new to that factory</div></div>
        <div class="card box stat"><div class="v">{pct(H['repeat_detected_in_new_state'],0)}</div><div class="l">of repeats found in a state new to that factory</div></div>
        <div class="card box stat"><div class="v">{pct(H['top10pct_firms_share'],0)}</div><div class="l">of all failures from 10% of factories (Gini {H['gini']:.2f})</div></div>
      </div>
      <div class="grid2" style="margin-top:12px">
        <div class="card box"><b style="font-size:11.5px">Does it depend on how names are matched?</b>
          {bars([("Exact strings", abl['exact string']['repeat_share'], '#cbd5e1', pct(abl['exact string']['repeat_share'])),
                 ("Normalised names", abl['normalised name, same state']['repeat_share'], '#94a3b8', pct(abl['normalised name, same state']['repeat_share'])),
                 ("DawaDrishti (default)", abl['fuzzy ≥92, same state (default)']['repeat_share'], '#e11d48', pct(abl['fuzzy ≥92, same state (default)']['repeat_share'])),
                 ("Factories joined across states", abl['fuzzy ≥92, units joined across states (firm)']['repeat_share'], '#fb7185', pct(abl['fuzzy ≥92, units joined across states (firm)']['repeat_share']))], "48%")}
          <p class="faint" style="font-size:9.5px;margin-top:4px">Above exact strings, every rule gives 63–68%. Missed merges lower the share, so ours is conservative.</p></div>
        <div class="card box"><b style="font-size:11.5px">The honest counter-finding</b>
          <table style="margin-top:4px"><tr><th>Case</th><th class="r">Alerts before</th><th class="r">Total</th></tr>
          {''.join(f"<tr><td>{c['case']}</td><td class='r'><b class='rose'>{c['alerts_before_incident']}</b></td><td class='r'>{c['national_alerts']}</td></tr>" for c in cases)}</table>
          <p style="font-size:10px;margin-top:6px">The national alerts alone would not have warned anyone about these three. So the memory must also take <b>state-lab and buyer results</b>, which is the next step on our roadmap.</p></div>
      </div>
      <h3>Step 6 · Build: can AI realistically help?</h3>
      <p>Yes, but mostly with careful data work, not a big model. The hard part is <b>knowing which names are the same factory</b>, at precision high enough to name firms safely.
      Then come simple, auditable rules at the moment of decision. Prediction helps regulators decide where to sample, and it is held to the standard of beating simple rules.</p>
      {foot(5, T)}</div>""")
    # 6 the solution
    pages.append(f"""<div class="page"><div class="eyebrow">The solution</div><h2 class="d">A national quality memory, and a lookup every buyer can call</h2>
      <p>DawaDrishti is <b>not another ERP</b> and <b>not a blacklist</b>. It is the layer that has to exist before a shared ERP would be worth anything. It is a public-record aggregator with
      a risk signal for buyers, and it plugs into the systems buyers already run.</p>
      <div class="grid3" style="margin-top:10px">
        <div class="card box"><span class="pill teal">Public</span><h3>Anyone</h3><p>Look up a manufacturer. See every published failure, with month, medicine, test failed, lab and batch. Also shown: the as-of date, what the data can't tell you, and how to request a correction. No predictions.</p></div>
        <div class="card box"><span class="pill amber">Buyer</span><h3>Procurement officer</h3><p>At purchase order: a graded response with supply concentration beside it. At goods receipt: a batch already on the national list is held at once. Issue stays blocked until the lab clears the batch.</p></div>
        <div class="card box"><span class="pill indigo">Regulator</span><h3>Drug controller</h3><p>Where to sample next: units ranked by future regulatory attention, with the alerts behind each rank. A conformance engine checks buyers' event logs for stock released before testing.</p></div>
      </div>
      <h3>The graded response (same rules in the API and in the console)</h3>
      <table><tr><th style="width:9%">Level</th><th style="width:22%">Response</th><th>When</th><th style="width:30%">In the buyer's ERP</th></tr>
        <tr><td><b class="rose">3</b></td><td><b>Pause new orders</b></td><td>A critical failure in the last 12 months, or debarred by a buyer</td><td>PO blocked unless an override is recorded</td></tr>
        <tr><td><b style="color:#ea580c">2</b></td><td><b>Test every batch</b></td><td>A critical failure 13–36 months ago, or 2+ alerts in 12 months</td><td>No skip-lot testing</td></tr>
        <tr><td><b style="color:#d97706">1</b></td><td><b>Prefer alternatives</b></td><td>Any alert in the last 36 months</td><td>At equal price, choose another supplier</td></tr>
        <tr><td><b style="color:#059669">0</b></td><td><b>No recent record</b></td><td>Nothing in 36 months</td><td>Absence of a record, not a certificate</td></tr></table>
      <div class="grid2" style="margin-top:12px;align-items:start">
        <div><h3 style="margin-top:0">The link is the factory, and the batch is a bonus</h3><p>Alerts carry the manufacturer's batch numbers and no buyer. So a buyer's own stock matches an alert by batch only when it bought that exact batch.
          That is rare, but decisive: the batch is held on arrival. Everything else works at factory level, which is where the 64.9% signal lives.</p>
</div>
        <img class="shot" src="{img('check_candidates')}">
      </div>
      <h3>A buyer's journey with DawaDrishti</h3>
      <div class="grid4">
        {''.join(f'<div class="card box"><div class="num">{i}</div><b style="display:block;margin-top:6px;font-size:12px">{t}</b><p>{d}</p></div>' for i, t, d in [
          (1, 'Raise a purchase order', 'The ERP calls the lookup for each supplier on the rate contract.'),
          (2, 'See the graded response', 'Traffic lights per supplier, with how concentrated supply is.'),
          (3, 'Receive the goods', 'The batch number is checked against the national list; a match is held.'),
          (4, 'Release only when cleared', 'Issue is blocked until the lab clears the batch. Every step is logged.')])}
      </div>
      {foot(6, T)}</div>""")
    # 7 product tour
    pages.append(f"""<div class="page"><div class="eyebrow">Product tour · live at {LIVE.replace('https://','')}</div><h2 class="d">What it looks like</h2>
      <div class="grid2" style="gap:14px">
        <div><img class="shot" src="{img('check_buyer')}"><p style="font-size:9.5px;margin-top:5px"><b>Check a manufacturer, buyer view.</b> 38 published failures; the graded response is "Test every batch"; the model's estimate is labelled with its tested accuracy.</p></div>
        <div><img class="shot" src="{img('buyers_suppliers')}"><p style="font-size:9.5px;margin-top:5px"><b>For buyers, step 2.</b> Suppliers on the rate contract, each with its traffic-light response. Supply concentration and days of cover shown first.</p></div>
        <div><img class="shot" src="{img('buyers_held')}"><p style="font-size:9.5px;margin-top:5px"><b>Goods receipt.</b> This exact batch already failed a government test, so it is held on arrival and the supplier is notified.</p></div>
        <div><img class="shot" src="{img('buyers_blocked')}"><p style="font-size:9.5px;margin-top:5px"><b>Release.</b> Issue to hospitals is refused until the lab clears the batch. Every step lands in the event log that process mining reads.</p></div>
      </div>
      <div style="display:flex;gap:12px;margin-top:12px;align-items:center">
        <img src="{img('phone_home')}" style="width:34mm;border-radius:10px;border:1px solid #e3e8ef"><img src="{img('phone_check')}" style="width:34mm;border-radius:10px;border:1px solid #e3e8ef">
        <p style="flex:1">Designed for non-experts: four sections (Home, Check, For buyers, How we know), plain language, motion that explains (the ring fills, numbers count up, a blocked release shakes), and it works on a phone.
          The <b>How we know</b> section holds every piece of evidence: the study, data quality, models, process checks, patterns, and a question box.</p></div>
      {foot(7, T)}</div>""")
    # 8 how it works
    pages.append(f"""<div class="page"><div class="eyebrow">How it works</div><h2 class="d">Architecture</h2>
      <div class="card" style="padding:14px;margin-top:4px">{architecture(0.85)}</div>
      <table style="margin-top:12px"><tr><th style="width:20%">Component</th><th>Method</th><th style="width:30%">Checked by</th></tr>
        <tr><td><b>Extraction</b></td><td>Portal JSON (2019–26) and pdfplumber for PDFs (2017–18). Rule-based cleaning of name, address, state (last place named wins), product, failure type and severity</td><td>Audit against the portal: {pct(AUDIT['row_precision'])} of rows match; fields agree 96.7–99.8%</td></tr>
        <tr><td><b>Entity resolution</b></td><td>Normalisation rules, blocking, fuzzy scoring, union-find. Unit = firm + state; firm = units joined across states. Score 80–92 goes to a person</td><td>200 labelled pairs (120 development, 80 held out); threshold sweep</td></tr>
        <tr><td><b>Warehouse</b></td><td>DuckDB star schema. Two fact tables (failures, buyer events) share supplier, product and date dimensions</td><td>Rebuilt from source by one command</td></tr>
        <tr><td><b>Lookup API</b></td><td>FastAPI. Name resolution (candidates below the threshold), record, graded response, exact-batch check, alternatives</td><td>Policy tests: no score in the public view; key-gated buyer view</td></tr>
        <tr><td><b>Conformance engine</b></td><td>Declarative rules (precedence, response within N days, requires) plus process discovery. Written from scratch, because pm4py is AGPL</td><td>Identical to hand-written checks; BPI 2019 reproduced</td></tr>
        <tr><td><b>Models</b></td><td>Gradient boosting with a time split: future regulatory attention (real), batch test priority (simulated)</td><td>AUC and top-k against simple rules; confound checks</td></tr>
        <tr><td><b>Questions</b></td><td>Gemini (or keyword rules) picks one of nine SQL templates; parameters are validated against the data and bound</td><td>Injection tests; never writes SQL</td></tr>
        <tr><td><b>Interface</b></td><td>React, Tailwind, framer-motion, Recharts and Leaflet, served by the API in one Docker image</td><td>Phone and desktop checks; 22 automated tests</td></tr>
      </table>
      <div class="grid3" style="margin-top:12px">
        <div class="card box stat"><div class="v">5,521 → {n(ER['population']['units'])}</div><div class="l">name strings resolved into factories ({n(ER['population']['firms'])} firms)</div></div>
        <div class="card box stat"><div class="v">~190 MB</div><div class="l">memory in production: runs on a free Render instance</div></div>
        <div class="card box stat"><div class="v">1 command</div><div class="l"><span class="mono">python -m dawadrishti build</span> rebuilds everything from the public data</div></div>
      </div>
      {foot(8, T)}</div>""")
    # 9 evaluation
    rows = "".join(f"<tr><td>{a}</td><td><span class='pill {'teal' if b == 'Real' else 'amber'}'>{b}</span></td><td class='r'><b>{c}</b></td><td>{d}</td></tr>" for a, b, c, d in eval_rows())
    m = FT["results"]
    pages.append(f"""<div class="page"><div class="eyebrow">Evaluation</div><h2 class="d">Every claim, against a baseline</h2>
      <table><tr><th style="width:30%">Question</th><th style="width:10%">Data</th><th class="r" style="width:14%">Result</th><th>Against what</th></tr>{rows}</table>
      <div class="grid2" style="margin-top:12px">
        <div class="card box"><b style="font-size:11.5px">Who will appear in the next 6 months of alerts? (real)</b><p class="faint" style="font-size:9.5px">Trained up to Sep 2025, tested on Mar–Aug 2026: {n(FT['universe'])} units, {n(FT['positives'])} appeared</p>
          {bars([(k, v['auc'] - 0.4, c, f"{v['auc']:.3f}") for (k, v), c in zip(m.items(), ['#0d9488', '#94a3b8', '#94a3b8', '#e2e8f0'])], "44%")}
          <p class="faint" style="font-size:9.5px;margin-top:4px">AUC (bars start at 0.4). On the top 50 alone, "most recent failure" wins: {pct(m['Most recent failure']['top50']['precision'],0)} vs {pct(m['Attention model (ML)']['top50']['precision'],0)}. We say so.</p></div>
        <div class="card box"><b style="font-size:11.5px">Is it only learning where inspectors look?</b>
          <table style="margin-top:4px"><tr><th>Units scored</th><th class="r">Model</th><th class="r">Simple rule</th></tr>
          {''.join(f"<tr><td>{g['group']}</td><td class='r'>{g['model_auc']:.3f}</td><td class='r'>{g['most_recent_failure_auc']:.3f}</td></tr>" for g in CONF['groups'])}
          <tr><td>next failure found by a new lab ({CONF['detected_elsewhere'][0]['units']})</td><td class='r'>{CONF['detected_elsewhere'][0]['model_auc']:.3f}</td><td class='r'>{CONF['detected_elsewhere'][0]['most_recent_failure_auc']:.3f}</td></tr></table>
          <p class="faint" style="font-size:9.5px;margin-top:4px">A model that knows only the state scores {CONF['state_only_baseline_auc']:.3f}.</p></div>
      </div>
      <div class="grid2" style="margin-top:12px">
        <div class="card box"><b style="font-size:11.5px">Name matching on held-out hard pairs</b>
          {bars([("Exact names", ERT['Exact name']['test']['firm']['recall'], '#cbd5e1', '0.00'),
                 ("Earlier rules (v1)", ERT['Fuzzy ≥92, v1 rules (before fixes)']['test']['firm']['recall'], '#94a3b8', f"{ERT['Fuzzy ≥92, v1 rules (before fixes)']['test']['firm']['recall']:.2f}"),
                 ("DawaDrishti (v2)", ERT['Fuzzy ≥92, v2 rules']['test']['firm']['recall'], '#4f46e5', f"{ERT['Fuzzy ≥92, v2 rules']['test']['firm']['recall']:.2f}"),
                 ("v2 + human review", ER['with_human_review']['recall_if_reviewers_confirm']['test']['firm']['recall'], '#0d9488', f"{ER['with_human_review']['recall_if_reviewers_confirm']['test']['firm']['recall']:.2f}")], "44%")}
          <p class="faint" style="font-size:9.5px;margin-top:4px">Recall shown; precision is 1.00 for every automatic rule, so no false merges. Labels were made by the assistant and await human review.</p></div>
        <div class="card box"><b style="font-size:11.5px">Conformance engine on a log we did not write</b>
          <table style="margin-top:4px"><tr><th>BPI Challenge 2019 (SAP)</th><th class="r">Published</th><th class="r">Ours</th></tr>
          {''.join(f"<tr><td>{k.replace('_',' ')}</td><td class='r'>{n(BPI['reader_check']['published'][k])}</td><td class='r'>{n(BPI['reader_check']['ours'][k])}</td></tr>" for k in ['events','cases','purchase_documents','activities'])}</table>
          <p style="font-size:9.5px;margin-top:4px">{n(BPI['rules'][0]['violating_cases'])} invoices paid before goods receipt; <b>0</b> where SAP enforces the rule. Enforced rules hold, policies leak, which is why DawaDrishti enforces "no issue before clearance".</p></div>
      </div>
      <h3>How we tested</h3>
      <p><b>Time splits</b> for every model: trained only on the past, scored on months it never saw. <b>Held-out sets</b> for name matching: test pairs drawn after the rules were fixed, labelled with scores hidden.
        <b>Baselines</b> everywhere: simple rules a regulator or buyer would otherwise use. <b>Uncertainty</b> by cluster bootstrap. <b>Robustness</b> by recomputing the headline under five matching rules.
        <b>Simulated results are labelled</b> and never presented as measured outcomes.</p>
      {foot(9, T)}</div>""")
    # 10 responsible by design
    pages.append(f"""<div class="page"><div class="eyebrow">Responsible by design</div><h2 class="d">Naming real firms, carefully</h2>
      <p>DawaDrishti names real manufacturers, so how it names them is part of the design. It is a <b>public-record aggregator with a risk signal for buyers, not a blacklist</b>.
        A blacklist asserts a conclusion. We present evidence that already exists, assembled in one place, with its provenance attached.</p>
      <div class="grid2" style="margin-top:8px">
        {''.join(f'<div class="card box"><b>{t}</b><p>{d}</p></div>' for t, d in [
          ('Public pages show records, never predictions', 'The API enforces it: public responses carry no score and no ranked list. The buyer view can require a key.'),
          ('Every figure is dated', 'Each answer carries the as-of date and a list of what the data does not contain: passing batches, licence actions, harm, sampling effort.'),
          ('A correction route on every record', 'Anyone can ask for a correction or an annotation. A regulatory_action field is filled only from a cited order.'),
          ('No guessed identities', "An unclear name returns candidates to choose from, never one firm's record under another firm's name."),
          ('Fakes are not counted against the victim', 'A fake whose named firm denied making it is excluded (45 rows), and so is a row naming a buyer instead of a maker (35).'),
          ('The language model never characterises a firm', 'It only picks one of nine reviewed query templates. Its parameters are checked against the data before anything runs.')])}
      </div>
      <h3>Data, and what is real</h3>
      <table><tr><th>Data</th><th>Status</th><th>Licence / note</th></tr>
        <tr><td>CDSCO NSQ alerts 2017–2026 ({n(STUDY['data']['records_used'])} used)</td><td><span class="pill teal">Real</span></td><td>Government of India public information; re-downloadable by script</td></tr>
        <tr><td>BPI Challenge 2019 SAP event log</td><td><span class="pill teal">Real</span></td><td>4TU.ResearchData; not committed (728 MB), but the result is</td></tr>
        <tr><td>Five buyers' ERP history (orders, batches, tests, debarments)</td><td><span class="pill amber">Simulated</span></td><td>Seeded generator, assumptions in docs/ASSUMPTIONS.md; supplier names and records are real</td></tr>
        <tr><td>Entity-resolution labels (200 pairs)</td><td><span class="pill indigo">Assistant-labelled</span></td><td>Awaiting human review; a blind review tool is included</td></tr>
      </table>
      <h3>How it looks on a record</h3>
      <img class="shot" src="{img('check_record')}" style="width:100%;height:64mm;object-fit:cover;object-position:top">
      {foot(10, T)}</div>""")
    # 11 open source: try, run, extend
    pages.append(f"""<div class="page"><div class="eyebrow">Open source</div><h2 class="d">Try it, run it, extend it</h2>
      <h3 style="margin-top:4px">Real input and output</h3>
      <p>One GET request from any ERP at purchase order and goods receipt. Below is a real response, trimmed.</p>
      <div class="card" style="padding:10px 12px;font-size:9px;line-height:1.45;background:#0f172a;color:#e2e8f0;border:none;margin-top:6px"><span class="mono" style="color:#5eead4">$ curl "{LIVE.replace('https://','')}/api/v1/lookup?q=Nestor%20Pharmaceuticals%20Ltd&amp;view=buyer&amp;batch=CITB-02&amp;molecule=Ciprofloxacin"</span>
        <pre class="mono" style="white-space:pre-wrap;margin-top:6px">{example_json()}</pre></div>
      <div class="grid2" style="margin-top:12px">
        <div class="card box"><b style="font-size:12px">Open-source checklist</b>
          <table style="margin-top:4px">
            {''.join(f"<tr><td>{a}</td><td class='r'><b class='teal'>✓</b> {b}</td></tr>" for a, b in [
              ('Licence', 'MIT'), ('README: run steps, example, limitations', 'yes'), ('Architecture, evaluation, assumptions', 'docs/'),
              ('Data sources and licences', 'ACKNOWLEDGEMENTS.md'), ('CONTRIBUTING + correction template', 'yes'), ('Automated tests', '22 passing'),
              ('One-command rebuild from public data', 'yes'), ('Docker image, live URL', 'Render (free)'), ('Secrets kept out of the repo', '.env.example'),
              ('v1.0 tag and release', 'GitHub')])}</table></div>
        <div><h3 style="margin-top:0">Run it yourself</h3>
          <div class="card" style="padding:10px 12px;font-size:9.5px"><span class="mono">git clone {REPO}.git<br>cd dawadrishti<br>docker build -t dawadrishti .<br>docker run -p 8000:8000 dawadrishti<br># open http://localhost:8000</span></div>
          <h3>Where help is most useful</h3>
          <ul><li>Reviewing the 200 name-matching labels (a blind review tool is included)</li><li>A route for state labs and buyers to send results in</li>
            <li>A DVDMS / e-Aushadhi connector that calls the lookup</li><li>Product mapping to WHO ATC and India's NLEM</li></ul></div>
      </div>
      {foot(11, T)}</div>""")
    # 12 limitations + roadmap + sources
    src = "".join(f"<li><a href='{u}'>{t}</a></li>" for t, u in SOURCES)
    pages.append(f"""<div class="page"><div class="eyebrow">Limits, next steps, sources</div><h2 class="d">What this does not do yet</h2>
      <ul>
        <li><b>Alerts list failures, not tests.</b> No failure rate per factory, so we measure repetition on the record.</li>
        <li><b>Sampling is uneven.</b> The prediction is of regulatory attention, not true quality, and is never shown publicly.</li>
        <li><b>The national list misses state findings.</b> Coldrif, Maiden and Kaysons had no prior national alert. That needs the contribution route below.</li>
        <li><b>Name-matching labels</b> are the assistant's until people review them. Recall on the hardest pairs is 0.63; missed merges make the headline conservative.</li>
        <li><b>Buyer-side results are simulated.</b> The network effect and batch priority show the method, not a measured outcome.</li>
      </ul>
      <h3>Roadmap</h3>
      <div class="grid3">
        <div class="card box"><span class="pill teal">Next 3 months</span><p style="margin-top:6px">Human review of the labels. A contribution route for state labs and buyers to send failures in. A correction workflow.</p></div>
        <div class="card box"><span class="pill indigo">6 months</span><p style="margin-top:6px">Pilot with one state medical-services corporation: call the lookup from its ERP at PO and goods receipt; measure orders changed.</p></div>
        <div class="card box"><span class="pill amber">12 months</span><p style="margin-top:6px">DVDMS / e-Aushadhi connector. A licence master for true alternatives. Real buyer event logs into the conformance engine.</p></div>
      </div>
      <h3>Team</h3>
      <p><b>Abhishek Jadli</b> (<a href="https://github.com/AbhishekJadli007">@AbhishekJadli007</a>). Solo entry: data pipeline, entity resolution, study, API, conformance engine, models, interface, deployment and documentation.
        An AI assistant (Claude) helped with research and code, every part reviewed. See ACKNOWLEDGEMENTS.md.</p>
      <h3>Sources</h3><ul style="font-size:9.5px">{src}</ul>
      <div class="callout" style="margin-top:10px"><b>Find the problem. Prove it matters. Build the solution. Commit it to open source.</b><br>
        <span style="font-size:10.5px">Live: <a href="{LIVE}">{LIVE.replace('https://','')}</a> · Code: <a href="{REPO}">{REPO.replace('https://','')}</a> · Licence: MIT</span></div>
      {foot(12, T)}</div>""")
    return pages


# =====================================================================================================  2-page brief
def brief() -> list[str]:
    m = FT["results"]
    p1 = f"""<div class="page"><div style="display:flex;align-items:center;gap:10px">{logo(34)}<div><div class="d" style="font-weight:800;font-size:18px">DawaDrishti · Solution brief</div>
        <div style="font-size:9.5px;color:#526077">COMMIT FOR GOOD 2026 · AI for Resilient and Sustainable Supply Chains · Abhishek Jadli</div></div>
        <div style="margin-left:auto;text-align:right;font-size:9.5px"><a href="{LIVE}">{LIVE.replace('https://','')}</a><br><a href="{REPO}">{REPO.replace('https://','')}</a></div></div>
      <h1 class="d" style="font-size:28px;line-height:1.1;margin:14px 0 8px">Most failed medicines come from factories <span class="grad-alert">we already knew about.</span></h1>
      <div class="quote">{PROBLEM_SENTENCE}</div>
      <h3>Why it matters</h3>
      <div class="grid4">
        <div class="card box stat"><div class="v">3,104</div><div class="l">drug samples NSQ in 2024–25 (Lok Sabha)</div></div>
        <div class="card box stat"><div class="v">24</div><div class="l">children dead after Coldrif syrup, as of 15 Oct 2025 (ETV Bharat)</div></div>
        <div class="card box stat"><div class="v">40</div><div class="l">failures from one supplier, banned a year, then reinstated (DTE)</div></div>
        <div class="card box stat"><div class="v">0</div><div class="l">buyer ERPs that read CDSCO's national failure list</div></div></div>
      <h3>What exists, and the gap</h3>
      <p>CDSCO publishes every failed batch, but as monthly PDFs and a portal, with no factory identity and no API. Buyers' ERPs (DVDMS, e-Aushadhi) handle purchase and testing
        but never read the alerts. Risk-based inspection, started after the 2025 deaths, serves regulators, not the buyer about to order. <b>The evidence is public, but it isn't joined up by factory,
        isn't trusted enough to act on, and isn't there at the moment of purchase.</b></p>
      <div style="display:flex;gap:16px;align-items:center;margin-top:10px">
        {ring(H['repeat_share'], 150, 14, label='already on record')}
        <div style="flex:1"><h3 style="margin-top:0">What we found in nine years of alerts (real data)</h3>
          <ul><li><b>{pct(H['repeat_share'])}</b> of {n(STUDY['data']['records_used'])} failed batches came from a factory with an earlier alert (95% CI {pct(H['repeat_share_ci95'][0])}–{pct(H['repeat_share_ci95'][1])}).</li>
            <li>The next failure comes about <b>{H['median_months_first_to_next']:.0f} months</b> after the first. <b>{pct(H['repeat_detected_by_new_lab'],0)}</b> of repeats are found by a lab new to that factory.</li>
            <li><b>{pct(H['top10pct_firms_share'],0)}</b> of failures come from 10% of factories.</li>
            <li>With exact name matching it would look like <b>{pct(STUDY['ablation']['exact string']['repeat_share'])}</b>, because one factory is spelled up to 14 ways.</li>
            <li><b>Honest limit:</b> Coldrif, Maiden and Kaysons had <b>no</b> national alert before their incidents, so the memory must also take state-lab and buyer results.</li></ul></div></div>
      <div class="foot"><span>DawaDrishti · Solution brief</span><span>1 / 2</span></div></div>"""
    p2 = f"""<div class="page"><div class="eyebrow">Our solution</div><h2 class="d" style="font-size:20px">A national quality memory, and a lookup every buyer's ERP can call</h2>
      <p>{SOLUTION_SENTENCE} Not another ERP, and not a blacklist.</p>
      <div class="card" style="padding:10px;margin:10px 0">{architecture(0.72)}</div>
      <div class="grid2">
        <div><h3 style="margin-top:0">What it does</h3><ul>
          <li><b>Public lookup:</b> every published failure per factory, with as-of date, data limits and a correction link. No predictions.</li>
          <li><b>Buyer view:</b> graded response (pause / test every batch / prefer alternatives) plus supply concentration.</li>
          <li><b>Goods receipt:</b> a batch already on the national list is held on arrival. Issue is blocked until cleared.</li>
          <li><b>Regulator:</b> where to sample next; a conformance engine for buyers' event logs.</li></ul></div>
        <div><h3 style="margin-top:0">How we know (against baselines)</h3>
          <table><tr><th>Check</th><th class="r">Result</th></tr>
            <tr><td>PDF reader vs CDSCO portal</td><td class="r">{pct(AUDIT['row_precision'])} rows</td></tr>
            <tr><td>Name matching precision (held out)</td><td class="r">{ERT['Fuzzy ≥92, v2 rules']['test']['firm']['precision']:.2f}</td></tr>
            <tr><td>Next-6-month alerts: model vs best rule</td><td class="r">{m['Attention model (ML)']['auc']:.3f} vs {m['Most past failures']['auc']:.3f}</td></tr>
            <tr><td>Same, found by a new lab</td><td class="r">{CONF['detected_elsewhere'][0]['model_auc']:.3f}</td></tr>
            <tr><td>Real SAP log (BPI 2019): counts reproduced</td><td class="r">4 / 4</td></tr>
            <tr><td>Risk-first testing (simulated)</td><td class="r">{pct(BT['results']['DawaDrishti risk order']['caught_in_first_30pct'],0)} vs {pct(BT['results']['First in, first out']['caught_in_first_30pct'],0)}</td></tr></table></div></div>
      <div class="grid2" style="margin-top:10px">
        <div><h3 style="margin-top:0">Responsible by design</h3><p>Records only on public pages, enforced by the API. Every figure is dated. A correction route on every record. No guessed identities.
          The LLM only picks reviewed query templates. Simulated data is labelled.</p></div>
        <div><h3 style="margin-top:0">Next steps</h3><p><b>3 months:</b> human label review; state labs and buyers send results in. <b>6 months:</b> pilot with one state corporation's ERP.
          <b>12 months:</b> DVDMS / e-Aushadhi connector and a licence master for true alternatives.</p></div></div>
      <div class="grid2" style="margin-top:10px"><img class="shot" src="{img('check_buyer')}"><img class="shot" src="{img('buyers_held')}"></div>
      <div class="callout" style="margin-top:10px;font-size:10.5px"><b>Open source (MIT).</b> One-command rebuild from public data, 22 tests, Docker image, live demo on free hosting.
        Live: <a href="{LIVE}">{LIVE.replace('https://','')}</a> · Code: <a href="{REPO}">{REPO.replace('https://','')}</a></div>
      <div class="foot"><span>DawaDrishti · Solution brief</span><span>2 / 2</span></div></div>"""
    return [p1, p2]


# =====================================================================================================  deck
def deck() -> list[str]:
    m = FT["results"]
    S = []
    total = 12

    def slide(i, body, bg="#fff"):
        return f'<div class="slide" style="background:{bg}">{body}<div class="brand">{logo(20)} DawaDrishti</div><div class="sn">{i} / {total}</div></div>'
    S.append(slide(1, f"""<div style="display:flex;gap:56px;align-items:center;height:100%">
        <div style="flex:1.2"><div class="eyebrow" style="font-size:14px">COMMIT FOR GOOD 2026 · AI for Resilient and Sustainable Supply Chains</div>
          <h1 class="d" style="font-size:62px;margin-top:18px">Most failed medicines come from factories <span class="grad-alert">we already knew about.</span></h1>
          <p style="margin-top:24px;font-size:21px">DawaDrishti: a national memory of India's failed medicine batches, and a lookup every buyer can call before buying.</p>
          <p class="muted" style="margin-top:26px;font-size:16px">Abhishek Jadli · {LIVE.replace('https://','')} · github.com/AbhishekJadli007/dawadrishti</p></div>
        <div>{ring(H['repeat_share'], 400, 32, label='of failed batches came from a factory already on the national list', fs=0.19)}</div></div>""",
        "linear-gradient(150deg,#f0fdfa,#fff 50%,#eef2ff)"))
    S.append(slide(2, f"""<div class="eyebrow" style="font-size:14px">The problem</div><h2 class="d">Public buyers can't see a supplier's national record before they buy</h2>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-top:20px">
          {''.join(f'<div class="card" style="padding:22px"><div class="big" style="font-size:52px;color:{c}">{v}</div><p style="font-size:16px;margin-top:6px">{t}</p></div>' for v, t, c in [
            ('3,104', 'drug samples declared not of standard quality in 2024–25', '#0f172a'), ('24', 'children dead after Coldrif syrup, as of 15 Oct 2025', '#e11d48'),
            ('40', 'failures from one Rajasthan supplier: banned a year, then reinstated', '#d97706'), ('0', "buyer ERPs that read CDSCO's national failure list", '#4f46e5')])}</div>
        <div class="quote" style="margin-top:34px;font-size:24px;padding:22px 28px">CDSCO publishes every failed batch. Buyers' ERPs never read it. A supplier that fails in one state keeps winning orders in another.</div>"""))
    S.append(slide(3, f"""<div class="eyebrow" style="font-size:14px">Where it breaks</div><h2 class="d">The goods flow works. The information flow doesn't.</h2>
        <div class="card" style="padding:36px 28px 70px;margin-top:20px">{supply_chain(big=True)}</div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:26px">
          {''.join(f'<div class="card" style="padding:20px"><div class="d" style="font-weight:800;font-size:20px">{t}</div><p style="font-size:16px;margin-top:6px">{d}</p></div>' for t, d in [
            ('Late, incompatible information', 'Monthly PDFs and a portal page; one factory spelled up to 14 ways'),
            ('Local decisions ignore the network', "A buyer can't see a failure found in another state"),
            ('Single points of failure', 'Pausing a bad supplier must be weighed against supply')])}</div>"""))
    S.append(slide(4, f"""<div style="display:flex;gap:56px;align-items:center;height:100%">
        <div>{ring(H['repeat_share'], 360, 30, label='already on the record', fs=0.2)}</div>
        <div style="flex:1"><div class="eyebrow" style="font-size:14px">What we found · real CDSCO data, 2017–2026</div><h2 class="d">Two in three failures were predictable from the public record</h2>
          <ul><li><b>{pct(H['repeat_share'])}</b> of {n(STUDY['data']['records_used'])} failed batches came from a factory with an earlier alert (95% CI {pct(H['repeat_share_ci95'][0])}–{pct(H['repeat_share_ci95'][1])})</li>
            <li>Next failure about <b>{H['median_months_first_to_next']:.0f} months</b> after the first: time to act</li>
            <li><b>{pct(H['repeat_detected_by_new_lab'],0)}</b> of repeats found by a lab that had never caught that factory</li>
            <li><b>{pct(H['top10pct_firms_share'],0)}</b> of all failures from just 10% of factories</li></ul></div></div>"""))
    abl = STUDY["ablation"]
    S.append(slide(5, f"""<div class="eyebrow" style="font-size:14px">Why it's hard</div><h2 class="d">The same factory is spelled up to 14 different ways</h2>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:20px;align-items:center">
          <div class="card" style="padding:28px"><p style="font-size:17px;margin-bottom:14px">Share of failed batches that look like repeats</p>
            <div style="font-size:18px">{bars([("Exact names", abl['exact string']['repeat_share'], '#cbd5e1', pct(abl['exact string']['repeat_share'])), ("DawaDrishti", H['repeat_share'], '#e11d48', pct(H['repeat_share']))], "36%").replace('font-size:10.5px', 'font-size:18px').replace('height:9px', 'height:18px')}</div></div>
          <div><div class="card" style="padding:16px;margin-bottom:14px"><p style="font-size:14px;color:#526077">One factory, as written in the alerts ({EX['spellings']['count']} ways):</p>
            <div style="font-size:13px;margin-top:6px">{''.join(f'<span class="chip">{x}</span>' for x in EX['spellings']['names'][:10])}</div></div>
            <ul><li><b>{n(ER['population']['distinct_raw_strings'])}</b> raw name strings resolved into <b>{n(ER['population']['units'])}</b> factories</li>
            <li>Tested on held-out hard pairs: <b>precision 1.00</b>, so no false merges</li>
            <li>Uncertain pairs go to a <b>human review queue</b>, never guessed</li>
            <li>A PDF reader audited against CDSCO's portal: <b>{pct(AUDIT['row_precision'])}</b> of rows match</li></ul></div></div>"""))
    cases = STUDY["worked_cases"]
    S.append(slide(6, f"""<div class="eyebrow" style="font-size:14px">The honest part</div><h2 class="d">The disasters, checked against the record</h2>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin-top:20px">
          {''.join(f'<div class="card" style="padding:26px"><div class="d" style="font-size:22px;font-weight:800">{c["case"].split(" (")[0]}</div><div class="muted" style="font-size:15px">{c["note"]}</div><div class="big" style="font-size:72px;color:#e11d48;margin-top:12px">{c["alerts_before_incident"]}</div><p style="font-size:16px">national alerts before the incident ({c["national_alerts"]} in total)</p></div>' for c in cases)}</div>
        <p style="margin-top:28px">National alerts alone would not have caught these. So the memory must also take <b>state-lab and buyer results</b>, and that is our next step. We show this rather than hide it.</p>"""))
    S.append(slide(7, f"""<div class="eyebrow" style="font-size:14px">Our solution</div><h2 class="d">A national quality memory, and one lookup any ERP can call</h2>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin-top:14px">
          {''.join(f'<div class="card" style="padding:24px"><span class="pill {p}" style="font-size:13px">{t}</span><div class="d" style="font-size:22px;font-weight:800;margin-top:10px">{h}</div><p style="font-size:16px;margin-top:6px">{d}</p></div>' for p, t, h, d in [
            ('teal', 'Public', 'Anyone', 'Every published failure per factory, dated, with data limits and a correction link. No predictions.'),
            ('amber', 'Buyer', 'At order and delivery', 'A graded response and supply concentration. A batch already on the national list is held on arrival.'),
            ('indigo', 'Regulator', 'Where to sample', 'Units ranked by future regulatory attention, with the alerts behind each rank. Conformance checks on event logs.')])}</div>
        <table style="margin-top:22px"><tr><th>Level</th><th>Response</th><th>When</th></tr>
          <tr><td><b class="rose">3</b></td><td><b>Pause new orders</b></td><td>critical failure in 12 months, or debarred</td></tr><tr><td><b style="color:#ea580c">2</b></td><td><b>Test every batch</b></td><td>critical in 36 months, or 2+ alerts in 12</td></tr>
          <tr><td><b style="color:#d97706">1</b></td><td><b>Prefer alternatives</b></td><td>any alert in 36 months</td></tr></table>"""))
    S.append(slide(8, f"""<div class="eyebrow" style="font-size:14px">Demo · Check a manufacturer</div><h2 class="d" style="margin-bottom:12px">The record, in plain language, with a clear answer</h2>
        <img class="shot" src="{img('check_buyer')}" style="height:520px;width:auto;margin:0 auto">"""))
    S.append(slide(9, f"""<div class="eyebrow" style="font-size:14px">Demo · Inside a buyer's system (simulated buyers, real records)</div><h2 class="d" style="margin-bottom:14px">Held on arrival. Blocked until cleared.</h2>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:22px"><img class="shot" src="{img('buyers_held')}"><img class="shot" src="{img('buyers_blocked')}"></div>
        <p style="margin-top:20px">Order from a supplier marked "test every batch" → the delivered batch is already on CDSCO's list, so it is <b>held on arrival</b> → release is <b>refused</b> until the lab clears it. Every step is logged.</p>"""))
    S.append(slide(10, f"""<div class="eyebrow" style="font-size:14px">How it works</div><h2 class="d">From scattered PDFs to an answer at the moment of purchase</h2>
        <div class="card" style="padding:24px;margin-top:8px">{architecture(1.25)}</div>
        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-top:22px">
          {''.join(f'<div class="card" style="padding:16px"><div class="d" style="font-weight:800;font-size:19px;color:{c}">{t}</div><p style="font-size:14px;margin-top:4px;line-height:1.4">{d}</p></div>' for t, d, c in [
            ('Explain', 'entity resolution and the record per factory', '#0d9488'), ('Detect', 'exact-batch check; conformance rules', '#e11d48'),
            ('Recommend', 'graded response with the supply cost', '#d97706'), ('Predict', 'where to sample; which batch first', '#4f46e5'),
            ('Ask', 'the LLM picks a reviewed query; never writes SQL', '#0f172a')])}</div>"""))
    rows = "".join(f"<tr><td>{a}</td><td><span class='pill {'teal' if b == 'Real' else 'amber'}' style='font-size:12px'>{b}</span></td><td class='r'><b>{c}</b></td></tr>" for a, b, c, d in eval_rows())
    S.append(slide(11, f"""<div class="eyebrow" style="font-size:14px">Evidence</div><h2 class="d">Every claim, against a baseline</h2>
        <div style="display:grid;grid-template-columns:1.45fr 1fr;gap:30px"><table>{rows}</table>
        <div><div class="card" style="padding:22px"><p style="font-size:16px"><b>Where the simple rule wins, we say so:</b> on the top 50 alone, "most recent failure" beats our model ({pct(m['Most recent failure']['top50']['precision'],0)} vs {pct(m['Attention model (ML)']['top50']['precision'],0)}).</p></div>
          <div class="card" style="padding:22px;margin-top:16px"><p style="font-size:16px"><b>On a real SAP log</b> (1.6M events) our engine reproduced all 4 published counts and found {n(BPI['rules'][0]['violating_cases'])} payments before goods receipt, but none where SAP enforces the rule.</p></div></div></div>"""))
    S.append(slide(12, f"""<div style="display:grid;grid-template-columns:1fr 1fr;gap:44px;height:100%;align-items:center">
        <div><div class="eyebrow" style="font-size:14px">Responsible · open · next</div><h2 class="d">A public-record aggregator, not a blacklist</h2>
          <ul style="font-size:18px"><li>Public pages show records, never predictions (enforced by the API)</li><li>Every figure dated; data limits and a correction route on every record</li>
            <li>No guessed identities; fakes not counted against the firm they abuse</li><li>MIT · 22 tests · one-command rebuild · Docker · live demo</li></ul></div>
        <div><div class="card" style="padding:26px"><div class="eyebrow">Roadmap</div>
          <p style="margin-top:8px"><b>3 months:</b> human label review; state labs and buyers send results in</p><p><b>6 months:</b> pilot inside one state corporation's ERP</p><p><b>12 months:</b> DVDMS / e-Aushadhi connector; licence master</p></div>
          <div style="margin-top:24px;padding:26px;border-radius:18px;background:linear-gradient(135deg,#0d9488,#4f46e5);color:#fff">
            <div class="d" style="font-size:28px;font-weight:800">Try it</div><p style="color:#e0f2f1;font-size:18px;margin-top:6px">{LIVE.replace('https://','')}<br>github.com/AbhishekJadli007/dawadrishti</p></div></div></div>""",
        "linear-gradient(150deg,#ffffff,#f0fdfa)"))
    return S


async def render(html: str, path: Path, page_sel: str, width: int, height: int):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": width, "height": height})
        await pg.set_content(html, wait_until="networkidle")
        await pg.evaluate("document.fonts.ready")
        if path.suffix == ".pdf":
            await pg.pdf(path=str(path), print_background=True, prefer_css_page_size=True)
        await b.close()


async def preview(html: str, out_dir: Path, sel: str, width: int, height: int, prefix: str):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": width, "height": height})
        await pg.set_content(html, wait_until="networkidle")
        await pg.evaluate("document.fonts.ready")
        for i, el in enumerate(await pg.query_selector_all(sel), 1):
            await el.screenshot(path=str(out_dir / f"{prefix}_{i:02d}.png"))
        # overflow check: any page whose content is taller than the page
        over = await pg.evaluate(f"""[...document.querySelectorAll('{sel}')].map((e, i) => [i + 1, e.scrollHeight - e.clientHeight]).filter(x => x[1] > 2)""")
        await b.close()
        return over


def wrap(css: str, pages: list[str], title: str) -> str:
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{css}</style></head><body>{''.join(pages)}</body></html>"


async def main(preview_dir: str | None = None):
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(wrap(DOC_CSS, solution_document(), "DawaDrishti — Solution document"), OUT / "DawaDrishti_Solution_Document.pdf", ".page", 794, 1123, "doc"),
            (wrap(DOC_CSS, brief(), "DawaDrishti — Solution brief"), OUT / "DawaDrishti_Solution_Brief.pdf", ".page", 794, 1123, "brief"),
            (wrap(DECK_CSS, deck(), "DawaDrishti — Presentation"), OUT / "DawaDrishti_Presentation.pdf", ".slide", 1280, 720, "deck")]
    for html, path, sel, w, h, prefix in jobs:
        await render(html, path, sel, w, h)
        print("wrote", path.relative_to(ROOT), f"{path.stat().st_size / 1e6:.1f} MB")
        if preview_dir:
            over = await preview(html, Path(preview_dir), sel, w, h, prefix)
            print("  overflowing pages:", over or "none")


if __name__ == "__main__":
    import sys
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
