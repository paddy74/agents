---
name: docs-pass
description: Checks a repo's docs (docs/, README.md, AGENTS.md, CLAUDE.md) against the code and data they describe and fixes stale facts, data/doc mismatches, and duplication across files. Use when asked for a docs pass or doc clean-up.
disable-model-invocation: true
---

# Docs pass

## Steps

1. Read docs/, README.md, AGENTS.md, and CLAUDE.md, plus the code, config, and data they describe.
2. Fix stale facts and mismatches between data and docs (e.g. evals.json vs. the spec).
3. Remove duplication across files: keep each fact in one place and link to it from the others.
4. Don't ask about routine fixes. Don't commit.
5. Report what changed then list any judgement calls.
