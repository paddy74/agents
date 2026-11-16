### Structure longer reference files with a table of contents

For reference files longer than 100 lines, include a table of contents at the top. This ensures Claude can see the full scope of available information even when previewing with partial reads.

**Example:**

```markdown
# API Reference

## Contents
- Authentication and setup
- Core methods (create, read, update, delete)
- Advanced features (batch operations, webhooks)
- Error handling patterns
- Code examples

## Authentication and setup
...

## Core methods
...
```

Claude can then read the complete file or jump to specific sections as needed.

For details on how this filesystem-based architecture makes progressive disclosure possible, see the [Runtime environment](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#runtime-environment) section later in this guide.
