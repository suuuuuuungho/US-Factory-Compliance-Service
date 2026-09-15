"""Assign hierarchical paragraph labels to parsed eCFR blocks."""

from __future__ import annotations

import re
from typing import Any


LEVELS = ["alpha", "num", "roman", "upper", "num", "roman"]

_LABEL = r"\([^()\s<>]{1,4}\)"
_ITALIC = r"<I>[\s\S]*?</I>"
_LEAD = re.compile(rf"^<[^>]+>\s*(?:(?:{_LABEL}\s*)+(?:{_ITALIC}[\s.:—-]*)?)+")
_TOKEN = re.compile(r"\(([^()\s<>]{1,4})\)")
_TERM_START = re.compile(r"^<[^>]+>\s*<I>([\s\S]*?)</I>")
_TERM_CHILDREN = re.compile(rf"^[\s.:—-]*((?:{_LABEL}\s*)+)")
_TAG = re.compile(r"<[^>]+>")

_Entry = tuple[int, str, str]
_Candidate = tuple[list[_Entry], str]


def _roman_value(token: str) -> int:
    values = {"i": 1, "v": 5, "x": 10}
    total = 0
    previous = 0
    for char in reversed(token):
        value = values[char]
        if value < previous:
            total -= value
        else:
            total += value
            previous = value
    return total


def _matches(cls: str, token: str) -> bool:
    if cls == "alpha":
        return re.fullmatch(r"[a-z]", token) is not None
    if cls == "num":
        return re.fullmatch(r"[0-9]{1,3}", token) is not None
    if cls == "roman":
        return re.fullmatch(r"x{0,3}(?:ix|iv|v?i{0,3})", token) is not None
    if cls == "upper":
        return re.fullmatch(r"[A-Z]", token) is not None
    return False


def _value(cls: str, token: str) -> int:
    if cls == "alpha":
        return ord(token) - ord("a") + 1
    if cls == "num":
        return int(token)
    if cls == "roman":
        return _roman_value(token)
    if cls == "upper":
        return ord(token) - ord("A") + 1
    raise ValueError(f"unknown label class: {cls}")


def _is_valid_token(token: str) -> bool:
    return any(_matches(cls, token) for cls in {"alpha", "num", "roman", "upper"})


def _valid_prefix(tokens: list[str]) -> list[str]:
    valid: list[str] = []
    for token in tokens:
        if not _is_valid_token(token):
            break
        valid.append(token)
    return valid


def _paragraph_tokens(markup: str) -> list[str]:
    match = _LEAD.match(markup)
    if match is None:
        return []
    lead = re.sub(_ITALIC, "", match.group(0))
    return _valid_prefix(_TOKEN.findall(lead))


def _definition(markup: str) -> tuple[str, list[str]] | None:
    match = _TERM_START.match(markup)
    if match is None:
        return None

    term = " ".join(_TAG.sub("", match.group(1)).split()).rstrip(",.:;")
    if not term:
        return None

    child_match = _TERM_CHILDREN.match(markup[match.end() :])
    child_tokens = []
    if child_match is not None:
        child_tokens = _valid_prefix(_TOKEN.findall(child_match.group(1)))
    return term, child_tokens


def _after(entry: _Entry, token: str) -> bool:
    _, previous, cls = entry
    return cls != "term" and _matches(cls, token) and _value(cls, token) > _value(cls, previous)


def _first_at(pos: int, token: str) -> bool:
    if not 0 <= pos < len(LEVELS):
        return False
    cls = LEVELS[pos]
    return _matches(cls, token) and _value(cls, token) == 1


def _candidates(stack: list[_Entry], token: str) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    top_pos = stack[-1][0] if stack else -1

    if stack and _after(stack[-1], token):
        pos, _, cls = stack[-1]
        candidates.append((stack[:-1] + [(pos, token, cls)], "sibling"))

    child_pos = top_pos + 1
    if _first_at(child_pos, token):
        candidates.append((stack + [(child_pos, token, LEVELS[child_pos])], "child"))

    for index in range(len(stack) - 2, -1, -1):
        entry = stack[index]
        if _after(entry, token):
            pos, _, cls = entry
            candidates.append((stack[:index] + [(pos, token, cls)], "ancestor"))

    for pos in range(top_pos + 2, len(LEVELS)):
        if _first_at(pos, token):
            candidates.append((stack + [(pos, token, LEVELS[pos])], "child_skip"))
            break

    return candidates


def _fallback(stack: list[_Entry], token: str) -> list[_Entry]:
    top_pos = stack[-1][0] if stack else -1
    for pos in range(min(top_pos + 1, len(LEVELS) - 1), -1, -1):
        cls = LEVELS[pos]
        if _matches(cls, token):
            kept = [entry for entry in stack if entry[0] < pos]
            return kept + [(pos, token, cls)]
    return list(stack)


def _append_first_below(stack: list[_Entry], token: str) -> list[_Entry] | None:
    top_pos = stack[-1][0] if stack else -1
    for pos in range(top_pos + 1, len(LEVELS)):
        if _first_at(pos, token):
            return stack + [(pos, token, LEVELS[pos])]
    return None


def _extend_consecutive(stack: list[_Entry], tokens: list[str]) -> list[_Entry] | None:
    result = list(stack)
    for token in tokens:
        pos = result[-1][0] + 1
        if not _first_at(pos, token):
            return None
        result.append((pos, token, LEVELS[pos]))
    return result


def _place_paragraph(
    stack: list[_Entry], tokens: list[str], next_tokens: list[str] | None
) -> tuple[list[_Entry], str]:
    first_candidates = _candidates(stack, tokens[0])
    complete: list[_Candidate] = []
    for candidate, method in first_candidates:
        extended = _extend_consecutive(candidate, tokens[1:])
        if extended is not None:
            complete.append((extended, method))

    if complete:
        if len(complete) > 1 and next_tokens:
            for candidate, method in complete:
                following = _candidates(candidate, next_tokens[0])
                if following and following[0][1] in {"sibling", "child", "ancestor"}:
                    return candidate, "ok"
        return complete[0][0], "ok"

    uncertain = False
    if first_candidates:
        result = first_candidates[0][0]
    else:
        result = _fallback(stack, tokens[0])
        uncertain = True

    for token in tokens[1:]:
        appended = _append_first_below(result, token)
        if appended is None:
            result = _fallback(result, token)
            uncertain = True
        else:
            result = appended
    return result, "uncertain" if uncertain else "ok"


def _replace_term(stack: list[_Entry], term: str) -> list[_Entry]:
    for index, entry in enumerate(stack):
        if entry[2] == "term":
            return stack[:index] + [(0, term, "term")]
    return stack + [(0, term, "term")]


def assign_label_paths(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return blocks with paragraph label paths and resolution statuses added."""

    tokens_by_block: list[list[str] | None] = []
    for block in blocks:
        if block.get("kind") == "paragraph":
            tokens_by_block.append(_paragraph_tokens(block.get("markup", "")))
        else:
            tokens_by_block.append(None)

    next_numbered: list[list[str] | None] = [None] * len(blocks)
    upcoming: list[str] | None = None
    for index in range(len(blocks) - 1, -1, -1):
        next_numbered[index] = upcoming
        tokens = tokens_by_block[index]
        if tokens:
            upcoming = tokens

    result: list[dict[str, Any]] = []
    stack: list[_Entry] = []
    for index, block in enumerate(blocks):
        output = dict(block)
        tokens = tokens_by_block[index]

        if tokens is None:
            status = "inherited"
        elif tokens:
            stack, status = _place_paragraph(stack, tokens, next_numbered[index])
        else:
            definition = _definition(block.get("markup", ""))
            if definition is None:
                status = "inherited"
            else:
                term, child_tokens = definition
                stack = _replace_term(stack, term)
                status = "ok"
                if child_tokens:
                    stack, child_status = _place_paragraph(
                        stack, child_tokens, next_numbered[index]
                    )
                    if child_status == "uncertain":
                        status = "uncertain"

        output["label_path"] = [entry[1] for entry in stack]
        output["label_status"] = status
        result.append(output)

    return result


__all__ = ["assign_label_paths"]
