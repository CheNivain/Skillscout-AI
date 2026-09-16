"""Repeatable retrieval metrics for the demonstration catalogue.

This is a small, labelled assignment dataset — not a production benchmark.
"""
from __future__ import annotations

import math

from backend.ai.engine import evaluation_queries, retrieve_courses
from backend.data.seed import get_seed_courses


def precision_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    if k < 1:
        raise ValueError("k must be positive")
    top = ranked[:k]
    if not top:
        return 0.0
    return sum(item in relevant for item in top) / k


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return sum(item in relevant for item in ranked[:k]) / len(relevant)


def mrr(ranked: list[str], relevant: set[str]) -> float:
    for index, item in enumerate(ranked, start=1):
        if item in relevant:
            return 1.0 / index
    return 0.0


def dcg(ranked: list[str], relevant: set[str], k: int) -> float:
    score = 0.0
    for index, item in enumerate(ranked[:k], start=1):
        gain = 1.0 if item in relevant else 0.0
        score += gain / math.log2(index + 1)
    return score


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    ideal = sum(1 / math.log2(index + 2) for index in range(min(k, len(relevant))))
    if ideal == 0:
        return 0.0
    return dcg(ranked, relevant, k) / ideal


def run_evaluation(k: int = 5) -> dict:
    if k < 1 or k > 50:
        raise ValueError("k must be between 1 and 50")
    courses = get_seed_courses()
    needs = {}  # Query retrieval is evaluated separately from employee personalisation.
    rows = []
    for item in evaluation_queries():
        ranked = [row["course"]["id"] for row in retrieve_courses(courses, needs, [], query=item["query"], limit=50)]
        relevant = set(item["relevant"])
        rows.append({
            "query": item["query"],
            "ranked": ranked[:k],
            "relevant": sorted(relevant),
            "p_at_k": round(precision_at_k(ranked, relevant, k), 3),
            "recall_at_k": round(recall_at_k(ranked, relevant, k), 3),
            "mrr": round(mrr(ranked, relevant), 3),
            "ndcg_at_k": round(ndcg_at_k(ranked, relevant, k), 3),
        })
    n = len(rows) or 1
    summary = {
        "k": k,
        "queries": len(rows),
        "catalogue_size": len(courses),
        "macro_p_at_k": round(sum(r["p_at_k"] for r in rows) / n, 3),
        "macro_recall_at_k": round(sum(r["recall_at_k"] for r in rows) / n, 3),
        "macro_mrr": round(sum(r["mrr"] for r in rows) / n, 3),
        "macro_ndcg_at_k": round(sum(r["ndcg_at_k"] for r in rows) / n, 3),
        "limitations": (
            f"Labels are author judgements over a {len(courses)}-course demonstration catalogue; "
            "this small development set is not a held-out or independently annotated benchmark. "
            "Scores are not comparable to web-scale IR benchmarks. Sparse synthetic posts "
            "also limit trend evaluation. LLM phrasing is excluded from these ranking metrics."
        ),
        "rows": rows,
    }
    return summary


def main() -> None:
    report = run_evaluation()
    print("SkillScout retrieval evaluation (labelled demo set)")
    print(f"  queries={report['queries']}  k={report['k']}")
    print(f"  P@{report['k']}={report['macro_p_at_k']}  Recall@{report['k']}={report['macro_recall_at_k']}  MRR={report['macro_mrr']}  NDCG@{report['k']}={report['macro_ndcg_at_k']}")
    print("  " + report["limitations"])
    for row in report["rows"]:
        print(f"  - {row['query']!r}: P={row['p_at_k']} R={row['recall_at_k']} MRR={row['mrr']} nDCG={row['ndcg_at_k']} top={row['ranked']}")


if __name__ == "__main__":
    main()
