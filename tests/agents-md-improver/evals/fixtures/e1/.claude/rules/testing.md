---
paths:
  - "tests/**/*.py"
---
# Testing rules

- Write tests as plain pytest functions with fixtures; don't use unittest.TestCase.
- Name test files `test_<module>.py`, mirroring `src/ledgerly/`.
- Use `tmp_path` for files; never write into the repository.
