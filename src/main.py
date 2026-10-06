"""End-to-end demo for the deterministic hallucination verifier.

Run from the repository root:
    python src/main.py

Outputs:
    report.html
    results.json
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from graph_engine import VerificationEngine
from nlp_extractor import ClaimExtractor, DynamicGraphBuilder


RULES = {
    ("CONTROLS", "ACTIVATES"): "INFLUENCES",
}


def matrix_html(matrix, labels):
    if not matrix:
        return "<p>No matrix available.</p>"
    out = ["<table class='matrix'><thead><tr><th></th>"]
    out.extend(f"<th>{html.escape(x)}</th>" for x in labels)
    out.append("</tr></thead><tbody>")
    for i, row in enumerate(matrix):
        out.append(f"<tr><th>{html.escape(labels[i])}</th>")
        out.extend(f"<td class='{'one' if v else 'zero'}'>{v}</td>" for v in row)
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def result_card(result, claim):
    verdict = result["verdict"]
    cls = verdict.lower()
    path = " → ".join(result.get("path", [])) or "—"
    rule = result.get("rule", "—")
    missing = ", ".join(result.get("missing_entities", [])) or "—"
    return f"""
    <article class='result-card {cls}'>
      <div class='result-top'>
        <div>
          <div class='eyebrow'>CLAIM {html.escape(str(claim['id']).zfill(2))}</div>
          <h3>{html.escape(claim['text'])}</h3>
        </div>
        <span class='badge'>{html.escape(verdict)}</span>
      </div>
      <div class='triplet'>
        <span>{html.escape(claim['parsed']['subject'])}</span>
        <b>— {html.escape(claim['parsed']['predicate'])} →</b>
        <span>{html.escape(claim['parsed']['object'])}</span>
      </div>
      <p class='reason'>{html.escape(result.get('reason', ''))}</p>
      <div class='evidence'>
        <div><span>Proof type</span><strong>{html.escape(result.get('proof_type', '—'))}</strong></div>
        <div><span>Path</span><strong>{html.escape(path)}</strong></div>
        <div><span>Rule</span><strong>{html.escape(rule)}</strong></div>
        <div><span>Missing entities</span><strong>{html.escape(missing)}</strong></div>
      </div>
    </article>
    """


def generate_report(document_text, ai_response, entities, engine, claims, results, output_path):
    counts = {v: sum(1 for r in results if r["verdict"] == v) for v in ["VERIFIED", "CONTRADICTED", "UNSUPPORTED", "UNRESOLVED"]}
    labels = list(entities.values())
    generated = datetime.now().strftime("%d %b %Y, %H:%M")
    hallucination_candidates = sum(1 for r in results if r['verdict'] in {'CONTRADICTED', 'UNSUPPORTED'})
    cards = "".join(result_card(r, c) for c, r in zip(claims, results))
    route_matrix = engine.predicate_matrix("ROUTES")
    controls = engine.predicate_matrix("CONTROLS")
    activates = engine.predicate_matrix("ACTIVATES")
    composed = engine.boolean_matrix_multiply(controls, activates)

    html_doc = f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Deterministic Hallucination Verification Report</title>
<style>
:root{{--bg:#08111f;--panel:#101c2e;--panel2:#15243a;--line:#243550;--text:#edf4ff;--muted:#91a4bd;--accent:#7c9cff;--green:#31d69a;--red:#ff6678;--amber:#ffca5c;--cyan:#54d7ff}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 80% -10%,#20386b 0,transparent 38%),var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.55}}
.wrap{{max-width:1180px;margin:auto;padding:36px 22px 70px}} header{{padding:34px;border:1px solid var(--line);border-radius:24px;background:linear-gradient(135deg,rgba(124,156,255,.20),rgba(84,215,255,.06));box-shadow:0 24px 70px rgba(0,0,0,.25)}}
.kicker,.eyebrow{{font-size:11px;letter-spacing:.16em;font-weight:800;color:var(--cyan)}} h1{{font-size:38px;line-height:1.1;margin:10px 0 12px}} h2{{font-size:22px;margin:0 0 14px}} h3{{font-size:17px;margin:4px 0 0}} p{{color:var(--muted)}}
.sub{{max-width:800px;font-size:15px}} .grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0 28px}} .stat,.panel,.result-card{{background:rgba(16,28,46,.88);border:1px solid var(--line);border-radius:18px}}
.stat{{padding:20px}} .stat b{{display:block;font-size:30px}} .stat span{{color:var(--muted);font-size:12px}} .panel{{padding:24px;margin:18px 0}} .results{{display:grid;gap:14px}}
.result-card{{padding:20px;border-left:4px solid var(--accent)}} .result-card.verified{{border-left-color:var(--green)}} .result-card.contradicted{{border-left-color:var(--red)}} .result-card.unsupported{{border-left-color:var(--amber)}} .result-card.unresolved{{border-left-color:var(--cyan)}}
.result-top{{display:flex;justify-content:space-between;gap:20px;align-items:flex-start}} .badge{{padding:7px 11px;border-radius:999px;font-size:11px;font-weight:900;letter-spacing:.08em;background:var(--accent)}} .verified .badge{{background:var(--green);color:#062419}} .contradicted .badge{{background:var(--red)}} .unsupported .badge{{background:var(--amber);color:#342500}} .unresolved .badge{{background:var(--cyan);color:#03212a}}
.triplet{{margin-top:16px;padding:13px 15px;border-radius:12px;background:var(--panel2);font-family:ui-monospace,SFMono-Regular,monospace;font-size:13px}} .triplet b{{color:var(--cyan)}} .reason{{margin:14px 0 10px}} .evidence{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}} .evidence div{{background:#0b1728;border:1px solid var(--line);padding:10px;border-radius:10px;min-height:62px}} .evidence span{{display:block;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.08em}} .evidence strong{{display:block;margin-top:4px;font-size:12px;word-break:break-word}}
table{{width:100%;border-collapse:collapse;font-size:12px}} th,td{{border:1px solid var(--line);padding:8px;text-align:center}} th{{background:var(--panel2);color:var(--muted)}} td.one{{background:rgba(49,214,154,.20);color:var(--green);font-weight:800}} td.zero{{color:#50647e}} .math{{font-family:Georgia,serif;font-size:18px;color:#dce8ff}} .source{{white-space:pre-wrap;background:#0a1525;border:1px solid var(--line);padding:18px;border-radius:12px;color:#bdcbe0;font-family:ui-monospace,monospace;font-size:12px}}
footer{{margin-top:30px;color:#647894;font-size:11px;text-align:center}} @media(max-width:800px){{.grid,.evidence{{grid-template-columns:repeat(2,1fr)}}h1{{font-size:30px}}}} @media(max-width:520px){{.grid,.evidence{{grid-template-columns:1fr}}}}
</style></head>
<body><main class='wrap'>
<header><div class='kicker'>DISCRETE MATHEMATICS × NEURO-SYMBOLIC VERIFICATION</div><h1>AI Hallucination Verification Report</h1><p class='sub'>This run treats the text in <b>ai_response.txt</b> as simulated AI output. Each generated claim is converted into a symbolic triple and checked against the trusted source graph using deterministic relations, matrices, contradictions, and explicit inference rules.</p><p>Generated {generated} · Ground truth: ground_truth.txt · AI response: ai_response.txt</p></header>
<section class='grid'>
<div class='stat'><b>{len(entities)}</b><span>ENTITIES</span></div><div class='stat'><b>{len(engine.edges)}</b><span>GROUND-TRUTH EDGES</span></div><div class='stat'><b>{len(claims)}</b><span>AI CLAIMS TESTED</span></div><div class='stat'><b>{hallucination_candidates}</b><span>HALLUCINATION CANDIDATES</span></div>
</section>
<section class='panel'><h2>AI response being tested</h2><div class='source'>{html.escape(ai_response)}</div></section>
<section class='panel'><h2>Verification overview</h2><div class='grid' style='margin-bottom:0'><div class='stat'><b>{counts['CONTRADICTED']}</b><span>CONTRADICTED</span></div><div class='stat'><b>{counts['UNSUPPORTED']}</b><span>UNSUPPORTED</span></div><div class='stat'><b>{counts['UNRESOLVED']}</b><span>UNRESOLVED</span></div><div class='stat'><b>100%</b><span>DETERMINISTIC RUN</span></div></div></section>
<section class='panel'><h2>Claims and proof traces</h2><p>The verifier never treats an arbitrary graph path as proof. A claim is verified only by an exact predicate edge or an explicitly declared logical rule.</p><div class='results'>{cards}</div></section>
<section class='panel'><h2>Discrete mathematics evidence</h2><p class='math'>For a predicate p, A<sub>p</sub>[i,j] = 1 iff the labeled edge (v<sub>i</sub>, p, v<sub>j</sub>) exists.</p><h3>ROUTES adjacency matrix A<sub>ROUTES</sub></h3>{matrix_html(route_matrix, labels)}
<h3 style='margin-top:24px'>Rule composition</h3><p class='math'>A<sub>CONTROLS</sub> ⊙ A<sub>ACTIVATES</sub> = A<sub>INFLUENCES</sub></p>{matrix_html(composed, labels)}
</section>
<section class='panel'><h2>Ground-truth source</h2><div class='source'>{html.escape(document_text)}</div></section>
<footer>Prototype research artifact · Deterministic verification is guaranteed relative to the extracted knowledge graph and declared rule set; it does not by itself guarantee real-world truth.</footer>
</main></body></html>"""
    output_path.write_text(html_doc, encoding="utf-8")


def main():
    source_path = ROOT / "ground_truth.txt"
    ai_response_path = ROOT / "ai_response.txt"
    output_path = ROOT / "report.html"
    json_path = ROOT / "results.json"

    document_text = source_path.read_text(encoding="utf-8")
    ai_response = ai_response_path.read_text(encoding="utf-8")
    builder = DynamicGraphBuilder()
    entities, edges = builder.extract_triplets_from_text(document_text)
    engine = VerificationEngine(entities, edges)
    extractor = ClaimExtractor()

    claims = []
    results = []
    for index, text_claim in enumerate([line.strip() for line in ai_response.splitlines() if line.strip()], start=1):
        parsed = extractor.extract_claim(text_claim)
        claim = {"id": index, "text": text_claim, "parsed": parsed}
        result = engine.verify_claim(parsed["subject"], parsed["predicate"], parsed["object"], RULES)
        claims.append(claim)
        results.append(result)

    generate_report(document_text, ai_response, entities, engine, claims, results, output_path)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "entities": entities,
        "edges": [e.__dict__ for e in engine.edges],
        "ai_response": ai_response,
        "claims": claims,
        "results": results,
        "rules": {f"{a} + {b}": c for (a, b), c in RULES.items()},
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\nDeterministic Hallucination Detector")
    print("=" * 42)
    print(f"Entities: {len(entities)} | Edges: {len(edges)} | AI claims: {len(claims)}")
    for claim, result in zip(claims, results):
        print(f"{result['verdict']:12} | {claim['text']}")
    print(f"\nReport: {output_path}")
    print(f"JSON:   {json_path}")


if __name__ == "__main__":
    main()
