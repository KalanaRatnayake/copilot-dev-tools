---
name: lint-fixer
description: 'Apply common Python lint cleanup for copied or migrated scripts. Use when fixing flake8-style import ordering, simple quote normalization, missing trailing newline, and basic long call or comment wrapping.'
argument-hint: 'Paths to Python files or directories to normalize, plus optional flags like --check or --recursive'
user-invocable: true
---

# Lint Fixer

Use this skill when a workspace has repetitive Python lint drift and the failures are mostly mechanical rather than semantic.

## Best Fit

- Fix import ordering between stdlib and non-stdlib imports.
- Normalize simple double-quoted literals and f-strings to single quotes when safe.
- Restore a trailing newline at end of file.
- Wrap long comment lines and simple call or signature lines.
- Run a dry-check before applying bulk edits.

## Not a Good Fit

- Rewriting complex multiline expressions.
- Correcting semantic bugs, typing issues, or failing tests.
- Reformatting C++ or XML.

## Procedure

1. Identify the Python files or directories with repeated lint failures.
2. Dry-run the fixer first:

```bash
python3 ./.agents/skills/lint-fixer/scripts/fix_python_lint_common.py --check path/to/file.py
```

3. Apply the rewrite once the preview is acceptable:

```bash
python3 ./.agents/skills/lint-fixer/scripts/fix_python_lint_common.py path/to/file.py
```

4. For a directory tree, pass `--recursive`.
5. Rerun the narrow lint command for only the touched files.

## Script

- Primary entrypoint: [fix_python_lint_common.py](./scripts/fix_python_lint_common.py)

## Notes

- The fixer implementation now lives directly in `./scripts/fix_python_lint_common.py` under this skill.
- If the remaining lint failures are down to a small set of `E302` or complex `E501` cases, finish those manually instead of widening the fixer.
