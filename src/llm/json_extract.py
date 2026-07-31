"""Extract JSON from LLM outputs (handles markdown fences, surrounding prose)."""

from __future__ import annotations


def extract_json(text: str) -> str:
    """Return the first JSON object/array substring from text."""
    t = text.strip()
    for marker in ("```json", "```JSON", "```"):
        if marker in t:
            start = t.index(marker) + len(marker)
            rest = t[start:]
            fence_end = rest.find("```")
            t = rest[:fence_end].strip() if fence_end != -1 else rest.strip()
            break

    for open_char, close_char in ("{", "}"), ("[", "]"):
        first = t.find(open_char)
        if first == -1:
            continue
        depth = 0
        for i in range(first, len(t)):
            ch = t[i]
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
            if depth == 0:
                return t[first : i + 1]

    return t