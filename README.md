# Copilot Dev Tools

Small shared tooling and Copilot skills used across local development workflows.

## Skills

| Skill | Path | Purpose |
| --- | --- | --- |
| `lint-fixer` | `.agents/skills/lint-fixer/` | Applies common Python lint cleanup for migrated or copied files. |

## Current Skill Details

### `lint-fixer`

- Skill file: `.agents/skills/lint-fixer/SKILL.md`
- Script: `.agents/skills/lint-fixer/scripts/fix_python_lint_common.py`
- Use it for repetitive Python cleanup such as:
  - import ordering
  - simple quote normalization
  - trailing newline restoration
  - basic long call/signature/comment wrapping

## Adding More Skills

1. Add a new folder under `.agents/skills/<skill-name>/`.
2. Add a `SKILL.md` with valid frontmatter.
3. Keep scripts and assets inside that skill folder when possible.
4. Update this README so there is one front-facing index of available tools.