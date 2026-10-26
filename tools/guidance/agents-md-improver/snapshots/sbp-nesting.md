### Avoid deeply nested references

Claude might partially read files when they're referenced from other referenced files. When encountering nested references, Claude might use commands such as `head -100` to preview content rather than reading entire files, resulting in incomplete information.

**Keep references one level deep from `SKILL.md`**. All reference files should link directly from `SKILL.md` to ensure Claude reads complete files when needed.

**Bad example: Too deep:**

```markdown
# SKILL.md
See [advanced.md](advanced.md)...

# advanced.md
See [details.md](details.md)...

# details.md
Here's the actual information...
```

**Good example: One level deep:**

```markdown
# SKILL.md

**Basic usage**: [instructions in SKILL.md]
**Advanced features**: See [advanced.md](advanced.md)
**API reference**: See [reference.md](reference.md)
**Examples**: See [examples.md](examples.md)
```
