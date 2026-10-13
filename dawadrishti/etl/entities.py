"""Entity resolution: which alert rows name the same manufacturer?

Two levels, decided up front (docs/ENTITY_RESOLUTION.md):
  unit  (manufacturer_id)  one manufacturing site = firm name + state. Licences are issued per site by the state,
                           so this is the level a regulator acts on and the level the memory keys on.
  firm  (firm_id)          all units of one firm across states. A buyer's rate contract is with the firm,
                           so profiles roll units up to the firm and say so.

Method: normalise the name (clean.name_key), block on the first 4 characters of the compacted key, score pairs
inside a block, and union every pair at or above the threshold. The threshold was chosen on labelled pairs.

Reviewer decisions (data/er/decisions.json, exported from the Quality page's review queue) override the matcher:
"same" joins two names even below the threshold, "different" stops that pair from being merged directly.
"""
from __future__ import annotations

import json
from collections import defaultdict

import pandas as pd
from rapidfuzz import fuzz

from .. import config as C
from . import clean

DECISIONS = C.DATA / "er" / "decisions.json"

UNIT_THRESHOLD = 92      # within a state
FIRM_THRESHOLD = 92      # across states


def score(a: str, b: str) -> float:
    """Similarity of two normalised keys, 0-100. Identical once spaces are removed counts as 100."""
    if clean.compact(a) == clean.compact(b):
        return 100.0
    return float(fuzz.token_sort_ratio(a, b))


def load_decisions(path=None) -> tuple[set, set]:
    """(must-link, cannot-link) sets of frozenset({key_a, key_b}) from the reviewers' exported decisions."""
    path = path or DECISIONS
    if not path.exists():
        return set(), set()
    must, cannot = set(), set()
    for d in json.loads(path.read_text()):
        a, b = (clean.name_key(x) for x in d["pair"][:2])
        if a == b:
            continue
        (must if d["decision"] == "same" else cannot).add(frozenset((a, b)))
    return must, cannot


def _union(n: int, blocks: dict, keys: list[str], threshold: float, pairs: list, level: str,
           cannot: set | None = None) -> list[int]:
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for idxs in blocks.values():
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                s = score(keys[i], keys[j])
                if s >= threshold and not (cannot and frozenset((keys[i], keys[j])) in cannot):
                    parent[find(j)] = find(i)
                    pairs.append((keys[i], keys[j], s, level))
    return [find(i) for i in range(n)]


def resolve(names: pd.Series, states: pd.Series, unit_threshold: float = UNIT_THRESHOLD,
            firm_threshold: float = FIRM_THRESHOLD, decisions: tuple[set, set] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (one row per distinct (key, state) with unit and firm group numbers, the merged pairs)."""
    must, cannot = decisions if decisions is not None else load_decisions()
    t = pd.DataFrame({"key": names.map(clean.name_key), "state": states.values})
    keys = t.groupby(["key", "state"]).size().reset_index(name="n")
    keys = keys[keys.key.str.len() > 2].sort_values("n", ascending=False).reset_index(drop=True)
    k = keys.key.tolist()
    block = [clean.compact(x)[:4] for x in k]
    pairs: list = []
    unit_blocks, firm_blocks = defaultdict(list), defaultdict(list)
    for i, (b, s) in enumerate(zip(block, keys.state)):
        unit_blocks[(b, s)].append(i)
    keys["unit"] = _union(len(keys), unit_blocks, k, unit_threshold, pairs, "unit", cannot)
    # firms: start from units, then join units across states
    reps = keys.drop_duplicates("unit")
    for i in reps.index:
        firm_blocks[block[i]].append(i)
    firm_of = dict(zip(reps.unit, _union_subset(reps.index.tolist(), firm_blocks, k, firm_threshold, pairs, cannot)))
    keys["firm"] = keys.unit.map(firm_of)
    if must:   # reviewer said "same": join the units (same state) or the firms (different states)
        for col, same_state in (("unit", True), ("firm", False)):
            parent: dict = {}

            def find(x):
                parent.setdefault(x, x)
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x
            for pair in must:
                a, b = tuple(pair)
                ra, rb = keys[keys.key.eq(a)], keys[keys.key.eq(b)]
                for _, x in ra.iterrows():
                    for _, y in rb.iterrows():
                        if (x.state == y.state) == same_state or (col == "firm"):
                            parent[find(y[col])] = find(x[col])
                            pairs.append((a, b, 100.0, f"{col} (reviewer)"))
            keys[col] = keys[col].map(lambda v: find(v))
        keys["firm"] = keys.groupby("unit").firm.transform("first")
    return keys, pd.DataFrame(pairs, columns=["key_a", "key_b", "score", "level"])


def _union_subset(idx: list[int], blocks: dict, keys: list[str], threshold: float, pairs: list, cannot=None) -> list[int]:
    pos = {i: p for p, i in enumerate(idx)}
    local = {b: [pos[i] for i in v] for b, v in blocks.items()}
    sub = [keys[i] for i in idx]
    roots = _union(len(idx), local, sub, threshold, pairs, "firm", cannot)
    return [idx[r] for r in roots]
