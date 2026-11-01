"""
Ranking benchmark runner.

Runs every gold-set query twice — baseline (fusion only, rerank OFF) vs composite
(rerank ON) — through the real retrieval stack in-process, and prints a
family-relevance comparison BROKEN OUT BY query_type (a global average hides the
case where the reranker helps descriptive queries but must not touch exact-name).

Usage (from ml_service/, with the DB + Qdrant already built):
    python -m eval.run              # dev split (tuning)
    python -m eval.run --test       # holdout split (final sign-off only)
    python -m eval.run --verbose    # + per-query nDCG deltas

This imports the full search stack (loads the embedding model), so it's a dev
tool, not part of the CI test suite (see tests/test_ranking.py for CI-safe checks).
"""
from __future__ import annotations

import sys
import json
import asyncio
from pathlib import Path
from collections import defaultdict

import vocab
import search_service
from eval import metrics

K = 10
CUT = 5
GOLD = Path(__file__).parent / "gold_set.json"


def _norm(s: str) -> str:
    return (s or "").lower().strip()


def _named_match(result: dict, expected: dict) -> bool:
    """Loose match: expected name is a prefix of the result name and the brand
    token overlaps — tolerant of concentration suffixes ('Aventus Cologne')."""
    rn, en = _norm(result.get("name")), _norm(expected["name"])
    if not (rn == en or rn.startswith(en) or en in rn):
        return False
    rb, eb = _norm(result.get("brand")), _norm(expected["brand"])
    return not eb or eb in rb or rb in eb


async def _search(query: str, ctx: dict, rerank: bool) -> list[dict]:
    return await search_service.hybrid_search(
        query, K, ctx.get("budget"), ctx.get("gender"), rerank=rerank)


def _score_query(entry: dict, results: list[dict]) -> dict:
    expected = set(entry.get("expected_families") or [])
    excluded = set(entry.get("excluded_families") or [])
    fams = [vocab.families_of(r.get("accords")) for r in results]
    gains = [metrics.family_gain(f, expected, excluded) for f in fams]

    out = {
        "ndcg": metrics.ndcg_at_k(gains, CUT),
        "fam_p": metrics.family_precision_at_k(fams, expected, CUT),
        "excl": metrics.exclusion_violation_rate(fams, excluded, CUT),
        "div": metrics.diversity_at_k(fams, CUT),
        "has_named": False, "recall": 0.0, "mrr": 0.0,
    }

    named = entry.get("expected_perfumes") or []
    if named:
        out["has_named"] = True
        grades, ranked_names = {}, []
        for r in results:
            hit = next((e for e in named if _named_match(r, e)), None)
            key = _norm(r.get("name")) + "|" + _norm(r.get("brand"))
            ranked_names.append(key)
            if hit:
                grades[key] = hit.get("grade", 1)
        expected_names = {k for k in grades}
        out["recall"] = metrics.recall_at_k(ranked_names, expected_names, CUT)
        out["mrr"] = metrics.mrr(ranked_names, expected_names)
    return out


def _fmt(v: float) -> str:
    return f"{v:.3f}"


def _delta(a: float, b: float) -> str:
    d = b - a
    sign = "+" if d >= 0 else ""
    return f"{sign}{d:.3f}"


async def main(split: str, verbose: bool) -> None:
    data = json.loads(GOLD.read_text(encoding="utf-8"))
    queries = [q for q in data["queries"] if q.get("split") == split]
    print(f"Ranking benchmark — split='{split}', {len(queries)} queries, "
          f"family metrics @{CUT}\n")

    # accumulator[query_type][metric][variant] = list of values
    agg: dict = defaultdict(lambda: defaultdict(lambda: {"base": [], "comp": []}))
    overall = defaultdict(lambda: {"base": [], "comp": []})

    for q in queries:
        ctx = q.get("context") or {}
        base = _score_query(q, await _search(q["query"], ctx, rerank=False))
        comp = _score_query(q, await _search(q["query"], ctx, rerank=True))
        qt = q["query_type"]
        for m in ("ndcg", "fam_p", "excl", "div", "recall", "mrr"):
            if m in ("recall", "mrr") and not base["has_named"]:
                continue
            agg[qt][m]["base"].append(base[m])
            agg[qt][m]["comp"].append(comp[m])
            overall[m]["base"].append(base[m])
            overall[m]["comp"].append(comp[m])
        if verbose:
            print(f"  [{qt:14}] nDCG {base['ndcg']:.3f}→{comp['ndcg']:.3f} "
                  f"({_delta(base['ndcg'], comp['ndcg'])})  "
                  f"excl {base['excl']:.2f}→{comp['excl']:.2f}   {q['query'][:48]}")

    if verbose:
        print()

    def avg(xs):
        return sum(xs) / len(xs) if xs else 0.0

    header = f"{'query_type':16} {'metric':7} {'baseline':>9} {'composite':>10} {'delta':>8}"
    print(header)
    print("-" * len(header))
    for qt in sorted(agg):
        for m in ("ndcg", "fam_p", "excl", "div", "recall", "mrr"):
            cells = agg[qt].get(m)
            if not cells or not cells["base"]:
                continue
            b, c = avg(cells["base"]), avg(cells["comp"])
            print(f"{qt:16} {m:7} {_fmt(b):>9} {_fmt(c):>10} {_delta(b, c):>8}")
        print()

    print("OVERALL")
    for m in ("ndcg", "fam_p", "excl", "div", "recall", "mrr"):
        b, c = avg(overall[m]["base"]), avg(overall[m]["comp"])
        print(f"{'':16} {m:7} {_fmt(b):>9} {_fmt(c):>10} {_delta(b, c):>8}")
    print("\nNotes: 'excl' lower is better; 'div' is a homogeneity diagnostic "
          "(not optimized); all others higher is better.")


if __name__ == "__main__":
    split = "test" if "--test" in sys.argv else "dev"
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    asyncio.run(main(split, verbose))
