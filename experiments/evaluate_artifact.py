"""Deterministic artifact-level checks reported by the public paper.

These checks test the released contract and implementation behavior.  They are
not a substitute for human judgments, real-world data, or online experiments.
"""

from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.engine import _poi_score, generate_case, generate_cases


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/public_cases.jsonl"
OUT = ROOT / "paper/artifact_evaluation.json"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]


def mutate_event(case: dict, field: str) -> dict:
    mutated = copy.deepcopy(case)
    event = mutated["context"]["event"]
    if field == "status":
        event["status"] = "expired"
    elif field == "distance_km":
        event["distance_km"] = 8.1
    elif field == "relevance":
        event["relevance"] = 0.59
    else:  # pragma: no cover - guarded by callers
        raise ValueError(field)
    mutated["expected_decision"] = "stay_silent"
    return mutated


def mutate_poi(case: dict, field: str) -> dict:
    mutated = copy.deepcopy(case)
    for poi in mutated["context"]["poi_candidates"]:
        if field == "status":
            poi["status"] = "closed"
        elif field == "distance_km":
            poi["distance_km"] = 5.1
        else:  # pragma: no cover - guarded by callers
            raise ValueError(field)
    mutated["expected_decision"] = "stay_silent"
    return mutated


def score_channels(case: dict) -> dict[str, float]:
    context = case["context"]
    all_scores: list[float] = []
    no_summary: list[float] = []
    no_preference: list[float] = []
    for poi in context.get("poi_candidates", []):
        full, _ = _poi_score(poi, context)
        all_scores.append(full)
        no_summary_poi = copy.deepcopy(poi)
        no_summary_poi["summary_theme"] = "__no_summary__"
        no_summary.append(_poi_score(no_summary_poi, context)[0])
        no_pref_context = copy.deepcopy(context)
        no_pref_context["user"]["preference_tags"] = []
        no_preference.append(_poi_score(poi, no_pref_context)[0])
    return {
        "mean_full_score": round(mean(all_scores), 4),
        "mean_score_without_summary": round(mean(no_summary), 4),
        "mean_score_without_preference": round(mean(no_preference), 4),
        "summary_mean_delta": round(mean(a - b for a, b in zip(all_scores, no_summary)), 4),
        "preference_mean_delta": round(mean(a - b for a, b in zip(all_scores, no_preference)), 4),
    }


def main() -> None:
    cases = load_cases()
    outputs = generate_cases(cases)
    rerun_outputs = generate_cases(cases)
    positive_events = [c for c in cases if c["card_type"] == "event" and c["expected_decision"] == "serve"]
    positive_pois = [c for c in cases if c["card_type"] == "poi" and c["expected_decision"] == "serve"]

    event_mutation_results = {}
    for field in ("status", "distance_km", "relevance"):
        mutated = [mutate_event(c, field) for c in positive_events]
        generated = generate_cases(mutated)
        event_mutation_results[field] = {
            "cases": len(mutated),
            "expected_silence": sum(c["expected_decision"] == "stay_silent" for c in mutated),
            "agreement": sum(g["decision"] == c["expected_decision"] for g, c in zip(generated, mutated)),
        }

    poi_mutation_results = {}
    for field in ("status", "distance_km"):
        mutated = [mutate_poi(c, field) for c in positive_pois]
        generated = generate_cases(mutated)
        poi_mutation_results[field] = {
            "cases": len(mutated),
            "expected_silence": sum(c["expected_decision"] == "stay_silent" for c in mutated),
            "agreement": sum(g["decision"] == c["expected_decision"] for g, c in zip(generated, mutated)),
        }

    noisy_cases = copy.deepcopy(cases)
    for case in noisy_cases:
        case["context"]["irrelevant_noise"] = {"unrelated_signal": "ignored"}
    noisy_outputs = generate_cases(noisy_cases)

    reversed_cases = copy.deepcopy(cases)
    for case in reversed_cases:
        if case["card_type"] == "poi":
            case["context"]["poi_candidates"].reverse()
    reversed_outputs = generate_cases(reversed_cases)

    silent_null = sum(o["decision"] == "stay_silent" and o.get("card") is None for o in outputs)
    summary_monotonicity = 0
    summary_comparisons = 0
    for case in positive_pois:
        context = case["context"]
        for poi in context.get("poi_candidates", []):
            full, _ = _poi_score(poi, context)
            no_summary_poi = copy.deepcopy(poi)
            no_summary_poi["summary_theme"] = "__no_summary__"
            ablated, _ = _poi_score(no_summary_poi, context)
            summary_comparisons += 1
            summary_monotonicity += int(ablated <= full)

    event_failures = Counter()
    for case in cases:
        if case["card_type"] == "event" and case["expected_decision"] == "stay_silent":
            event = case["context"]["event"]
            if event.get("status") != "active":
                event_failures["inactive"] += 1
            if float(event.get("distance_km", 99)) > 8:
                event_failures["too_far"] += 1
            if float(event.get("relevance", 0)) < 0.6:
                event_failures["weak_relation"] += 1

    summary_probe = [score_channels(c) for c in positive_pois]
    result = {
        "scope": "artifact_contract_checks",
        "case_count": len(cases),
        "distribution": {
            "card_type": dict(Counter(c["card_type"] for c in cases)),
            "expected_decision": dict(Counter(c["expected_decision"] for c in cases)),
            "card_and_decision": dict(Counter(f"{c['card_type']}_{c['expected_decision']}" for c in cases)),
            "event_themes": dict(Counter(c["context"]["event"]["theme"] for c in cases if c["card_type"] == "event")),
            "poi_candidate_count": dict(Counter(len(c["context"].get("poi_candidates", [])) for c in cases if c["card_type"] == "poi")),
        },
        "determinism": {"identical_rerun": outputs == rerun_outputs},
        "expected_decision_agreement": sum(o["decision"] == c["expected_decision"] for o, c in zip(outputs, cases)),
        "irrelevant_context_invariance": sum(a == b for a, b in zip(outputs, noisy_outputs)),
        "silent_card_null": silent_null,
        "poi_order_invariance": sum(
            a.get("selected_pois") == b.get("selected_pois")
            for a, b in zip(outputs, reversed_outputs)
            if a["card_type"] == "poi"
        ),
        "summary_non_increasing_after_ablation": {
            "comparisons": summary_comparisons,
            "passes": summary_monotonicity,
        },
        "event_negative_failure_modes": dict(event_failures),
        "event_one_factor_mutations": event_mutation_results,
        "poi_one_factor_mutations": poi_mutation_results,
        "poi_channel_probe": {
            "positive_case_count": len(summary_probe),
            "mean_across_cases": {
                key: round(mean(item[key] for item in summary_probe), 4)
                for key in summary_probe[0]
            },
        },
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
