"""Reproduce the fixed 51-case experiment subset and 10-case eye check."""

import json
import random
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).parent
CASES = HERE / "rag_eval_case_v2.jsonl"
OUTPUT = HERE / "rag_eval_subset.json"


def combo(case: dict) -> frozenset[str]:
    gold = set(case["gold_subparts"])
    return frozenset((gold - {"A"}) or gold)


def choose(cases: list[dict], target: int, rng: random.Random) -> list[dict]:
    groups: dict[frozenset[str], list[dict]] = defaultdict(list)
    for case in cases:
        groups[combo(case)].append(case)
    keys = sorted(groups, key=lambda value: tuple(sorted(value)))
    rng.shuffle(keys)
    for key in keys:
        groups[key].sort(key=lambda case: case["case_id"])
        rng.shuffle(groups[key])
    selected = []
    for round_number in range(2):
        for key in keys:
            if len(selected) == target:
                return selected
            if len(groups[key]) > round_number:
                selected.append(groups[key][round_number])
    if len(selected) != target:
        raise ValueError(f"Only {len(selected)} eligible cases for target {target}")
    return selected


def make_subset() -> dict[str, list[str]]:
    cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines()]
    rng = random.Random(273)
    adi = choose([case for case in cases if case["source"] == "adi"], 35, rng)
    dashboard = choose([case for case in cases if case["source"] == "dashboard"], 16, rng)
    subset = adi + dashboard
    rng.shuffle(subset)

    eye = []
    used = set()
    for source, target in (("adi", 7), ("dashboard", 3)):
        candidates = [case for case in subset if case["source"] == source]
        rng.shuffle(candidates)
        picked = 0
        for case in candidates:
            key = combo(case)
            if key not in used:
                eye.append(case)
                used.add(key)
                picked += 1
                if picked == target:
                    break
        if picked != target:
            raise ValueError(f"Only {picked} distinct eye cases for {source}")
    rng.shuffle(eye)
    return {"subset": [case["case_id"] for case in subset], "eye": [case["case_id"] for case in eye]}


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(make_subset(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
