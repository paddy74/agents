"""Static checks on the guidance workflow; it only runs on GitHub."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/guidance.yml"
EXPRESSION_RE = re.compile(r"\$\{\{[^}]*\}\}")


def workflow() -> dict[Any, Any]:
    """:return: The parsed workflow."""
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def steps() -> list[dict[str, Any]]:
    """:return: The steps of the single job."""
    return cast(list[dict[str, Any]], workflow()["jobs"]["refresh"]["steps"])


def test_env_paths_exist() -> None:
    """The manifest, references and skill paths the workflow uses exist."""
    env = cast(dict[str, str], workflow()["env"])
    for key in ("MANIFEST", "REFERENCES", "SKILL"):
        assert (REPO / env[key]).exists(), key


def test_prompt_file_exists() -> None:
    """The refresh prompt the Claude step follows exists."""
    prompts = [s["with"]["prompt"] for s in steps() if "prompt" in s.get("with", {})]
    assert len(prompts) == 1
    path = re.search(r"Follow (\S+)\.", prompts[0])
    assert path and (REPO / path.group(1)).is_file()


def test_actions_pinned_to_commits() -> None:
    """Every action is pinned to a full commit SHA."""
    uses = [s["uses"] for s in steps() if "uses" in s]
    assert uses
    assert all(re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", u) for u in uses), uses


def test_claude_uses_subscription_token() -> None:
    """Claude authenticates with the subscription OAuth token, not an API key."""
    (claude,) = [s for s in steps() if "claude-code-action" in s.get("uses", "")]
    token = claude["with"]["claude_code_oauth_token"]
    assert token == "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"
    assert "anthropic_api_key" not in claude["with"]


def test_never_pushes_to_default_branch() -> None:
    """Pushes go only to the bot branch."""
    pushes = [
        line.strip()
        for s in steps()
        for line in s.get("run", "").splitlines()
        if "git push" in line
    ]
    assert pushes == ['git push --force origin "$BRANCH"']
    assert workflow()["env"]["BRANCH"].startswith("bot/")


def run_scripts() -> list[str]:
    """:return: The ``run`` script of each step that has one."""
    return [s["run"] for s in steps() if "run" in s]


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
@pytest.mark.parametrize("index", range(len(run_scripts())))
def test_run_scripts_parse(index: int) -> None:
    """Each ``run`` script is valid bash once expressions are filled in."""
    filled = EXPRESSION_RE.sub("x", run_scripts()[index])
    subprocess.run(["bash", "-n"], input=filled, text=True, check=True)
