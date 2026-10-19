"""Markdown parsing helpers. Standard library only."""

from __future__ import annotations

import re

FENCE_OPEN_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")


def fence_mask(lines: list[str]) -> list[bool]:
    """Mark the lines that belong to fenced code blocks, fences included.

    A fence closes on a line of the same character at least as long as the opening
    run. A backtick fence whose info string contains a backtick isn't a fence.

    :param lines: Document lines.
    :return: ``True`` for each line inside (or opening/closing) a fence.
    """
    mask: list[bool] = []
    fence = ""
    for text in lines:
        if fence:
            mask.append(True)
            stripped = text.strip()
            if (
                stripped.startswith(fence)
                and set(stripped) == {fence[0]}
                and len(stripped) >= len(fence)
            ):
                fence = ""
            continue
        match = FENCE_OPEN_RE.match(text)
        if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
            fence = match.group(1)
            mask.append(True)
        else:
            mask.append(False)
    return mask
