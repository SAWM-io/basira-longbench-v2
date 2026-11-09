"""Recount the scores from the published answers, and sum the published reading figures.

No dependency, no network, no key.

  python3 -I recount.py

Reads answers/*.jsonl (official pred.py format: one line per question with `judge`)
and results.json, then prints:
  - accuracy overall / easy / hard / short / medium / long (same arithmetic as result.py),
  - Wilson 95% intervals, the paired comparison and the exact McNemar test,
  - tokens read by each condition, overall, on the long texts and on the texts cut for
    Opus alone, and what Opus alone would read on the long texts at the official 120,000 cap.

The scores and statistics are recomputed from the answers. The per-question reading
figures (prompt tokens, shares read, passage counts, recall times) are taken from the
run records and published in results.json: this script checks that they agree with
the answers and sums them, but cannot recompute them from this repository alone.
The memory figures of results.json (integrity checks, identity with the written
blocks) are likewise taken from the run.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = {"alone": "opus-5.5-alone_cot.jsonl", "with Basira": "opus-5.5-with-basira_rag-adaptive_cot.jsonl"}


def load(name: str) -> dict[str, dict]:
    lines = (HERE / "answers" / name).read_text(encoding="utf-8").splitlines()
    return {r["_id"]: r for r in (json.loads(line) for line in lines if line.strip())}


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return round(100 * (c - h), 1), round(100 * (c + h), 1)


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def main() -> None:
    answers = {c: load(f) for c, f in FILES.items()}
    print("Condition            Overall  Easy   Hard   Short  Medium Long   Wilson 95%")
    for c, rows in answers.items():
        def pct(f):
            sel = [r for r in rows.values() if f(r)]
            return 100 * sum(int(r["judge"]) for r in sel) / len(sel)
        k = sum(int(r["judge"]) for r in rows.values())
        lo, hi = wilson(k, len(rows))
        print(f"Opus 5.5 {c:<12} {pct(lambda r: True):6.1f} {pct(lambda r: r['difficulty'] == 'easy'):6.1f} "
              f"{pct(lambda r: r['difficulty'] != 'easy'):6.1f} {pct(lambda r: r['length'] == 'short'):6.1f} "
              f"{pct(lambda r: r['length'] == 'medium'):6.1f} {pct(lambda r: r['length'] == 'long'):6.1f}   "
              f"{lo}-{hi}  ({k}/{len(rows)}, {sum(1 for r in rows.values() if r['pred'] is None)} without letter)")
    a, b = answers["alone"], answers["with Basira"]
    assert set(a) == set(b)
    b_only = [i for i in a if b[i]["judge"] and not a[i]["judge"]]
    a_only = [i for i in a if a[i]["judge"] and not b[i]["judge"]]
    print(f"\nPaired on {len(a)} questions: right with Basira only {len(b_only)} {b_only}, right alone only {len(a_only)}; "
          f"exact McNemar p = {mcnemar_exact(len(b_only), len(a_only)):.3f}")

    res = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    pq = res["per_question"]
    assert {q["_id"] for q in pq} == set(a)
    for q in pq:  # the per-question table agrees with the answer files
        assert q["alone_correct"] == a[q["_id"]]["judge"] and q["basira_correct"] == b[q["_id"]]["judge"]
    def tot(field, length=None):
        return sum(q[field] for q in pq if length is None or q["length"] == length)
    ta, tb = tot("alone_tokens_read"), tot("basira_tokens_read")
    long_a, long_b = tot("alone_tokens_read", "long"), tot("basira_tokens_read", "long")
    print(f"\nTokens read (o200k): alone {ta:,}, with Basira {tb:,} ({ta / tb:.2f}x fewer with Basira)")
    print(f"Long texts: alone {long_a:,}, with Basira {long_b:,} ({100 * (1 - long_b / long_a):.1f}% fewer)")
    l120 = sum(min(q["text_tokens"], 120_000) for q in pq if q["length"] == "long")
    print(f"  (at the official 120,000 cap, Opus alone would read {l120:,} tokens on the long texts, but less of each text)")
    cut = [q for q in pq if q["alone_cut"]]
    print(f"Texts cut for Opus alone: {len(cut)}; tokens alone {sum(q['alone_tokens_read'] for q in cut):,}, "
          f"with Basira {sum(q['basira_tokens_read'] for q in cut):,}; correct alone {sum(q['alone_correct'] for q in cut)}/{len(cut)}, "
          f"with Basira {sum(q['basira_correct'] for q in cut)}/{len(cut)}")
    long_texts = sorted((q for q in pq if q["length"] == "long"), key=lambda q: -q["chars"])
    print("\nLong texts                         chars  alone tokens (share)       Basira tokens (share)  alone/Basira")
    for q in long_texts:
        print(f"{q['domain'][:30]:<30} {q['chars']:>10,}  {q['alone_tokens_read']:>9,} ({100 * q['alone_share_read']:5.1f}%{' cut' if q['alone_cut'] else '    '})"
              f"   {q['basira_tokens_read']:>9,} ({100 * q['basira_share_read']:5.1f}%)       "
              f"{'right' if q['alone_correct'] else 'wrong'}/{'right' if q['basira_correct'] else 'wrong'}")


if __name__ == "__main__":
    main()
