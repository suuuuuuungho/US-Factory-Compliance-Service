"""Produce conservative ECHO facility candidates for ADI documents."""

from __future__ import annotations

import re


_SUFFIX = {"INC", "LLC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LP", "L P", "L L C"}
_STATE_NAMES = {"ALABAMA": "AL", "GEORGIA": "GA", "NORTH CAROLINA": "NC", "INDIANA": "IN", "OHIO": "OH", "PENNSYLVANIA": "PA", "FLORIDA": "FL"}


def normalize_name(name) -> str:
    if not name:
        return ""
    value = re.sub(r"[^A-Z0-9& ]+", " ", str(name).upper()).replace("&", " AND ")
    words = value.split()
    while words and (words[-1] in _SUFFIX or " ".join(words[-2:]) in _SUFFIX):
        words.pop()
    return " ".join(words)


def _has_suffix(name) -> bool:
    words = re.sub(r"[^A-Z0-9& ]+", " ", str(name or "").upper()).split()
    return bool(words and (words[-1] in _SUFFIX or " ".join(words[-2:]) in _SUFFIX))


def states_in_text(text: str) -> set[str]:
    result = set(re.findall(r",\s*([A-Z]{2})\s+\d{5}(?:-\d{4})?", text))
    upper = text.upper()
    for name, code in _STATE_NAMES.items():
        if re.search(rf",\s*{re.escape(name)}\s+\d{{5}}", upper):
            result.add(code)
    return result


def build_facility_index(echo_rows: list[dict]) -> dict:
    index = {}
    for row in echo_rows:
        key = (normalize_name(row.get("name")), row.get("state"))
        if key[0] and key[1]:
            index.setdefault(key, set()).add((row["pgm_sys_id"], _has_suffix(row.get("name"))))
    return {key: sorted(value) for key, value in index.items()}


def extract_facility_candidates(document_id: str, facility_names: list, text: str, index: dict) -> list[dict]:
    states = states_in_text(text)
    rows, seen = [], set()
    for name in facility_names:
        normalized = normalize_name(name)
        if not normalized:
            continue
        for state in sorted(states):
            for pgm_sys_id, has_suffix in index.get((normalized, state), []):
                if has_suffix != _has_suffix(name):
                    continue
                if pgm_sys_id not in seen:
                    seen.add(pgm_sys_id)
                    rows.append({"document_id": document_id, "echo_pgm_sys_id": pgm_sys_id, "match_evidence": f"name:{normalized};state:{state}", "review_status": "검토 전"})
    return sorted(rows, key=lambda row: row["echo_pgm_sys_id"])
