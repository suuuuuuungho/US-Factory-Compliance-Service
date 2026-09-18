"""SUU-137: 검색 합격선. runs.jsonl의 기본 조합 최신 run이 이 선 아래면 실패다.

사용법 (레포 루트에서):
  python "[6] rag/eval/pass_line.py"   # 최신 기본 조합 run을 찾아 합격/불합격 출력. 불합격이면 exit 1

기본 조합 = hybrid(Kanon) + 규칙(SUU-134) + LLM 리랭크 gpt-5-mini(SUU-136), 평가셋 v2.
합격선 = 2026-09-18 점수(0.692 / 0.961 / 0.980)에서 동점 폭 0.03(≈ 3건)만큼 뺀 퇴보 방지선.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RUNS = Path(__file__).parent / "runs.jsonl"
DEFAULT_RUN = {"config": "hybrid", "eval_set_version": "v2", "rules": True, "llm_model": "gpt-5-mini"}
PASS_LINE = {"ndcg@10": 0.66, "hit@20": 0.95, "subpart@20": 0.95}


def is_default_run(run: dict) -> bool:
    return all(run.get(k) == v for k, v in DEFAULT_RUN.items())


def latest_default_run(runs: list[dict]) -> dict | None:
    """기본 조합 run 중 run_at이 가장 늦은 것. 없으면 None."""
    matches = [r for r in runs if is_default_run(r)]
    return max(matches, key=lambda r: r["run_at"]) if matches else None


def check_pass_line(run: dict) -> dict[str, tuple[float, float, bool]]:
    """지표 → (값, 합격선, 통과?)."""
    m = run["metrics"]
    values = {"ndcg@10": m["ndcg"]["10"], "hit@20": m["hit_loose"]["20"], "subpart@20": m["subpart_hit_primary"]["20"]}
    return {k: (round(values[k], 3), PASS_LINE[k], values[k] >= PASS_LINE[k]) for k in PASS_LINE}


def load_runs(path: Path = RUNS) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    run = latest_default_run(load_runs())
    if run is None:
        print("기본 조합 run이 runs.jsonl에 없다")
        return 1
    result = check_pass_line(run)
    for k, (value, line, ok) in result.items():
        print(f"{'OK  ' if ok else 'FAIL'} {k} {value:.3f} >= {line}")
    print(f"run: {run['run_id']}")
    return 0 if all(ok for _, _, ok in result.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
