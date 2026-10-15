"""Loads the pilot knowledge base (ragas, prayogas) from data/.  Join on SEMITONES, not swara names."""
import csv, json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
TOKEN_SEMI = {"S": 0, "R1": 1, "R2": 2, "R3": 3, "G1": 2, "G2": 3, "G3": 4, "M1": 5, "M2": 6, "P": 7,
              "D1": 8, "D2": 9, "D3": 10, "N1": 9, "N2": 10, "N3": 11}
# Context-free display names (used when no raga is known). Ambiguous semitones 2,3,9,10 default to R2,G2,D2,N2.
DEFAULT_NAMES = {0: "S", 1: "R1", 2: "R2", 3: "G2", 4: "G3", 5: "M1", 6: "M2", 7: "P", 8: "D1", 9: "D2", 10: "N2", 11: "N3"}
ALT_NAMES = {2: ["R2", "G1"], 3: ["R3", "G2"], 9: ["D2", "N1"], 10: ["D3", "N2"]}


def parse_scale(s):
    """"S R1 G3 S'" -> [0, 1, 4, 12]"""
    return [12 if t == "S'" else TOKEN_SEMI[t] for t in s.split()]


@dataclass
class Raga:
    name: str
    aro: list            # ascending semitone sequence (0..12), vakra repeats preserved
    avaro: list          # descending sequence (12..0)
    pcs: set
    names: dict          # semitone -> swara token used by this raga (e.g. 3 -> 'G2')
    meta: dict = field(default_factory=dict)

    @property
    def aro_pcs(self): return {x % 12 for x in self.aro}
    @property
    def avaro_pcs(self): return {x % 12 for x in self.avaro}


@lru_cache(maxsize=1)
def load_ragas():
    ragas = {}
    for r in json.load(open(DATA / "ragas_knowledge_base.json")):
        names = dict(DEFAULT_NAMES)
        for tok in (r["arohanam"] + " " + r["avarohanam"]).split():
            if tok != "S'": names[TOKEN_SEMI[tok]] = tok
        ragas[r["raga"]] = Raga(r["raga"], parse_scale(r["arohanam"]), parse_scale(r["avarohanam"]),
                                {int(x) for x in r["pitch_classes"].split()}, names, r)
    return ragas


def raga_names(): return list(load_ragas())


@lru_cache(maxsize=1)
def load_prayogas():
    """Expert-verified characteristic phrases. Ships EMPTY (Team Rule 4): fill data/prayoga_template.csv."""
    path, out = DATA / "prayoga_template.csv", {}
    if not path.exists(): return out
    for row in csv.DictReader(open(path, newline="")):
        if (row.get("verified_by_expert") or "").strip().upper() not in ("Y", "YES", "TRUE", "1"): continue
        try: seq = [TOKEN_SEMI[t] for t in row["phrase_swaras"].split()]
        except KeyError: continue
        out.setdefault(row["raga"], []).append({"id": row["prayoga_id"], "swaras": row["phrase_swaras"], "pcs": seq,
                                                "characteristic": row.get("is_characteristic(Y/N)", "Y")})
    return out


@lru_cache(maxsize=1)
def load_glossary():
    """Carnatic music terminology glossary from data/glossary.csv."""
    path = DATA / "glossary.csv"
    if not path.exists(): return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def load_swara_reference():
    """Swara variants, 12-TET cents and 5-limit Just Intonation ratios from data/swara_reference.csv."""
    path = DATA / "swara_reference.csv"
    if not path.exists(): return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

