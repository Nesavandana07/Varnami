"""Stage 4b: rule-based explanation.  Evidence comes from (1) the raga's scale grammar in the knowledge base,
(2) expert-verified prayogas if any are loaded (none ship with the pilot), (3) what separates the winner from the runner-up.
Scale-derived patterns are always labelled as such and are never presented as prayogas."""
from collections import Counter
from .knowledge import load_ragas, load_prayogas, DEFAULT_NAMES


def _pairs(seq): return {(a % 12, b % 12) for a, b in zip(seq, seq[1:]) if a % 12 != b % 12}


def grammar_pairs(raga):
    R = load_ragas()[raga]
    return {"asc": _pairs(R.aro), "desc": _pairs(R.avaro)}


def observed_moves(notes, max_gap=0.5):
    out = []
    for a, b in zip(notes, notes[1:]):
        if b["start"] - a["end"] <= max_gap and a["semitone"] != b["semitone"]:
            out.append(("asc" if b["semitone"] > a["semitone"] else "desc", a["pc"], b["pc"], a["end"]))
    return out


def scale_stats(notes, raga, present=0.03):
    R = load_ragas()[raga]
    tot = sum(n["dur"] for n in notes) or 1.0
    use = Counter()
    for n in notes: use[n["pc"]] += n["dur"] / tot
    off = {p: u for p, u in use.items() if p not in R.pcs and u > 0.01}
    moves = observed_moves(notes); G = grammar_pairs(raga)
    hit = sum((m[1], m[2]) in G[m[0]] for m in moves)
    dir_viol = [m for m in moves if (m[0] == "asc" and m[2] in R.avaro_pcs - R.aro_pcs) or
                (m[0] == "desc" and m[2] in R.aro_pcs - R.avaro_pcs)]
    return {"in_scale": 1 - sum(off.values()) - sum(u for p, u in use.items() if p not in R.pcs and u <= .01),
            "off_scale": off, "usage": dict(use), "missing": sorted(p for p in R.pcs if use.get(p, 0) < present),
            "grammar_hit": hit / len(moves) if moves else 0.0, "n_moves": len(moves), "dir_violations": len(dir_viol)}


def distinctive_moves(a, b, notes, top=4):
    """Directional moves in raga A's grammar that raga B lacks (and vice-versa), with observed counts."""
    GA, GB = grammar_pairs(a), grammar_pairs(b)
    cnt = Counter((d, f, t) for d, f, t, _ in observed_moves(notes))
    rows = []
    for d in ("asc", "desc"):
        for (f, t) in GA[d] - GB[d]: rows.append({"move": f"{DEFAULT_NAMES[f]}->{DEFAULT_NAMES[t]} ({d})", "favours": a, "count": cnt[(d, f, t)]})
        for (f, t) in GB[d] - GA[d]: rows.append({"move": f"{DEFAULT_NAMES[f]}->{DEFAULT_NAMES[t]} ({d})", "favours": b, "count": cnt[(d, f, t)]})
    return sorted(rows, key=lambda r: -r["count"])[:top]


def match_prayogas(notes, raga, max_gap=0.5):
    """Exact pitch-class phrase search over phrase-broken, repeat-collapsed note sequences."""
    P = load_prayogas().get(raga, [])
    seqs, cur = [], []
    for n in notes:
        if cur and (n["start"] - cur[-1]["end"] > max_gap): seqs.append(cur); cur = []
        if not cur or cur[-1]["pc"] != n["pc"]: cur.append(n)
    if cur: seqs.append(cur)
    hits = []
    for p in P:
        k, pc = len(p["pcs"]), [x % 12 for x in p["pcs"]]
        times = [round(s[i]["start"], 2) for s in seqs for i in range(len(s) - k + 1) if [x["pc"] for x in s[i:i + k]] == pc]
        hits.append({"id": p["id"], "phrase": p["swaras"], "count": len(times), "times": times[:10]})
    return {"n_loaded": len(P), "hits": [h for h in hits if h["count"]], "checked": len(P)}


def recurring_patterns(notes, raga, n=3, top=3):
    """Most frequent 3-note scale-legal patterns (NOT expert prayogas)."""
    G, c = grammar_pairs(raga), Counter()
    for a, b, d in zip(notes, notes[1:], notes[2:]):
        if b["start"] - a["end"] > .5 or d["start"] - b["end"] > .5: continue
        if a["pc"] != b["pc"] != d["pc"]:
            c[(a["pc"], b["pc"], d["pc"])] += 1
    names = load_ragas()[raga].names
    return [{"pattern": " ".join(names[p] for p in k), "count": v} for k, v in c.most_common(top) if v >= 3]


def explain(notes, probs, top_k=3):
    ranked = sorted(probs.items(), key=lambda kv: -kv[1])
    raga, conf = ranked[0]; runner, conf2 = ranked[1] if len(ranked) > 1 else (None, 0)
    R, S = load_ragas()[raga], scale_stats(notes, raga)
    names = R.names
    ev = []
    ev.append({"kind": "scale", "text": f"{S['in_scale']:.0%} of sung time stays on {raga}'s swaras ({' '.join(names[p] for p in sorted(R.pcs))})."})
    if S["off_scale"]: ev.append({"kind": "warning", "text": "Out-of-scale pitches present: " + ", ".join(f"{DEFAULT_NAMES[p]} ({u:.0%})" for p, u in sorted(S['off_scale'].items(), key=lambda kv: -kv[1])) + " - could be gamaka excursions, tracker error or a different raga."})
    if S["missing"]: ev.append({"kind": "warning", "text": "Swaras of this raga barely heard: " + ", ".join(names[p] for p in S['missing']) + "."})
    if S["n_moves"]: ev.append({"kind": "grammar", "text": f"{S['grammar_hit']:.0%} of {S['n_moves']} note-to-note moves are adjacent steps in {raga}'s arohanam/avarohanam (scale grammar, not prayogas)."})
    if S["dir_violations"]: ev.append({"kind": "warning", "text": f"{S['dir_violations']} moves use a swara in a direction where the raga normally omits it."})
    sep = []
    if runner:
        same = R.pcs == load_ragas()[runner].pcs
        sep = distinctive_moves(raga, runner, notes)
        if same: ev.append({"kind": "warning", "text": f"{raga} and {runner} use the same swaras, so the scale cannot separate them; the decision rests on directional movement and phrasing."})
        used = [s for s in sep if s["count"]]
        if used: ev.append({"kind": "contrast", "text": f"Versus {runner}: " + "; ".join(f"{s['move']} x{s['count']} favours {s['favours']}" for s in used[:3]) + "."})
    pr = match_prayogas(notes, raga)
    if pr["n_loaded"] == 0:
        ev.append({"kind": "prayoga", "text": "No expert-verified prayogas are loaded for this raga (data/prayoga_template.csv is empty), so no characteristic-phrase matching was done."})
        rec = recurring_patterns(notes, raga)
        if rec: ev.append({"kind": "pattern", "text": "Recurring scale-legal patterns (NOT expert prayogas): " + ", ".join(f"{r['pattern']} x{r['count']}" for r in rec) + "."})
    else:
        ev.append({"kind": "prayoga", "text": (f"Matched {len(pr['hits'])} of {pr['n_loaded']} verified prayogas: " + ", ".join(f"{h['phrase']} x{h['count']}" for h in pr['hits'])) if pr["hits"] else f"None of {pr['n_loaded']} verified prayogas found."})
    return {"raga": raga, "confidence": conf, "runner_up": runner, "margin": conf - conf2, "evidence": ev, "scale_stats": {**{k: v for k, v in S.items() if k not in ("usage", "off_scale", "missing")}, "off_scale": {DEFAULT_NAMES[p]: round(u, 3) for p, u in S["off_scale"].items()}, "missing": [names[p] for p in S["missing"]]},
            "usage": {DEFAULT_NAMES[p]: u for p, u in sorted(S["usage"].items())}, "prayogas": pr, "separating_moves": sep,
            "caveat": "Rules come from the unverified pilot sheet and no expert-verified prayogas are loaded; treat as decision support, not ground truth."}
