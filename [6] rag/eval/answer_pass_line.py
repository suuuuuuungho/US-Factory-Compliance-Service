"""SUU-155: 답변 합격선. answer_runs.jsonl의 기준 조합 최신 run이 이 선 아래면 실패다.

사용법 (레포 루트에서):
  python "[6] rag/eval/answer_pass_line.py"   # 최신 기준 조합 run을 찾아 합격/불합격 출력. 불합격이면 exit 1

기준 조합 = 평가셋 v2, 답에 넣는 조문 상위 10(SUU-152), 항상 넣는 Subpart A 조문 없음, 답변·심판 모두 gpt-5-mini.
합격선 = 상위 10 점수(0.961 / 0.739 / 0.996 / 1.775)에서 동점 폭 0.03(심판은 0.06, SUU-147)만큼 뺀 퇴보 방지선.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RUNS = Path(__file__).parent / "answer_runs.jsonl"
DEFAULT_RUN = {"eval_set_version": "v2", "top_n": 10, "always_sections": [],
               "answer_model": "gpt-5-mini", "judge_model": "gpt-5-mini"}
PASS_LINE = {"subpart": 0.93, "citation_recall": 0.70, "citation_grounded": 0.96, "judge": 1.71}


def is_default_run(run: dict) -> bool:
    # SUU-153 이전 run에는 always_sections 키가 없다. 없으면 []로 본다
    return all(run.get(k, [] if k == "always_sections" else None) == v for k, v in DEFAULT_RUN.items())


def latest_default_run(runs: list[dict]) -> dict | None:
    """기준 조합 run 중 run_at이 가장 늦은 것. 없으면 None."""
    matches = [r for r in runs if is_default_run(r)]
    return max(matches, key=lambda r: r["run_at"]) if matches else None


def check_pass_line(run: dict) -> dict[str, tuple[float, float, bool]]:
    """지표 → (값, 합격선, 통과?)."""
    m = run["metrics"]
    return {k: (round(m[k], 3), PASS_LINE[k], m[k] >= PASS_LINE[k]) for k in PASS_LINE}


def load_runs(path: Path = RUNS) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    run = latest_default_run(load_runs())
    if run is None:
        print("기준 조합 run이 answer_runs.jsonl에 없다")
        return 1
    result = check_pass_line(run)
    for k, (value, line, ok) in result.items():
        print(f"{'OK  ' if ok else 'FAIL'} {k} {value:.3f} >= {line}")
    print(f"run: {run['run_id']}")
    return 0 if all(ok for _, _, ok in result.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
