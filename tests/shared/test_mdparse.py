"""Tests for ``tools/shared/mdparse.py``."""

from __future__ import annotations

import pytest
from shared.mdparse import fence_mask


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a\n```\n# x\n```\nb", [False, True, True, True, False]),
        ("````\n```\n## y\n```\n````\nz", [True] * 5 + [False]),
        ("~~~\n```\n~~~\nq", [True, True, True, False]),
        ("```\n# open", [True, True]),
        ("``` a`b\ntext", [False, False]),
        ("```py\nx\n``` not-close\n```", [True, True, True, True]),
    ],
)
def test_fence_mask(text: str, expected: list[bool]) -> None:
    """Fences close on a same-character run at least as long as the opener."""
    assert fence_mask(text.split("\n")) == expected
