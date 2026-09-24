from __future__ import annotations

MAX_STATE_LENGTH = 255
MAX_TITLES = 3
TITLES_BEFORE_OVERFLOW = 2
SEPARATOR = " ... "
OVERFLOW = "and more!"


def _truncate_at_word(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut[: cut.rindex(" ")]
    return cut.rstrip(" ,;:-\u2013\u2014")


def _shares(lengths: list[int], budget: int) -> list[int]:
    allotted = [0] * len(lengths)
    pending = set(range(len(lengths)))
    remaining = budget

    while pending:
        share = remaining // len(pending)
        settled = [i for i in pending if lengths[i] <= share]
        if not settled:
            for i in pending:
                allotted[i] = share
            break
        for i in settled:
            allotted[i] = lengths[i]
            remaining -= lengths[i]
            pending.discard(i)

    return allotted


def build_ticker(titles: list[str | None], empty_state: str) -> str:
    titles = [t.strip() for t in titles if t and t.strip()]
    if not titles:
        return empty_state

    overflow = len(titles) > MAX_TITLES
    if overflow:
        titles = titles[:TITLES_BEFORE_OVERFLOW]

    budget = (
        MAX_STATE_LENGTH
        - len(SEPARATOR) * len(titles)
        - (len(OVERFLOW) if overflow else 0)
    )
    allotted = _shares([len(t) for t in titles], budget)

    parts: list[str] = []
    last_was_cut = False
    for title, limit in zip(titles, allotted, strict=True):
        cut = _truncate_at_word(title, limit)
        if not cut:
            continue
        parts.append(cut)
        last_was_cut = cut != title

    if not parts:
        return empty_state

    state = SEPARATOR.join(parts)
    if overflow:
        state += SEPARATOR + OVERFLOW
    elif last_was_cut:
        state += SEPARATOR.rstrip()
    return state[:MAX_STATE_LENGTH]
