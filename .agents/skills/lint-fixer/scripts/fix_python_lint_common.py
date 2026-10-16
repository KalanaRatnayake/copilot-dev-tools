#!/usr/bin/env python3

from __future__ import annotations

import argparse
import io
import re
import sys
import textwrap
import tokenize
from pathlib import Path
from typing import Iterable


SIMPLE_QUOTE_PATTERN = re.compile(
    r'(?<![A-Za-z0-9_])([rRuUbBfF]{0,2})"([^\'"\\\n]*)"'
)


def iter_python_files(paths: list[Path], recursive: bool) -> Iterable[Path]:
    for path in paths:
        if path.is_file() and path.suffix == '.py':
            yield path
            continue
        if path.is_dir():
            iterator = path.rglob('*.py') if recursive else path.glob('*.py')
            for child in sorted(iterator):
                if child.is_file():
                    yield child


def import_category(block: str) -> tuple[int, str]:
    first_line = block.splitlines()[0].strip()
    match = re.match(r'(?:from|import)\s+([A-Za-z0-9_\.]+)', first_line)
    module = match.group(1) if match else ''
    root = module.split('.', 1)[0]
    if root in sys.stdlib_module_names:
        return 0, module
    return 1, module


def collect_import_block(lines: list[str], start: int) -> tuple[int, list[str]]:
    index = start
    blocks: list[str] = []
    current: list[str] = []
    depth = 0
    in_import = False

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        starts_import = stripped.startswith('import ') or stripped.startswith('from ')

        if not in_import and not starts_import:
            if stripped == '':
                index += 1
                continue
            break

        if starts_import and not current:
            in_import = True

        if in_import:
            current.append(line)
            depth += line.count('(') - line.count(')')
            if depth <= 0 and stripped and not stripped.endswith('\\'):
                blocks.append(''.join(current))
                current = []
                in_import = False
            index += 1
            continue

        break

    if current:
        blocks.append(''.join(current))
    return index, blocks


def sort_top_imports(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines:
        return text

    index = 0
    prefix: list[str] = []
    while index < len(lines):
        stripped = lines[index].strip()
        if index == 0 and stripped.startswith('#!'):
            prefix.append(lines[index])
            index += 1
            continue
        if stripped.startswith('#') or stripped == '':
            prefix.append(lines[index])
            index += 1
            continue
        if stripped.startswith('from __future__ import '):
            prefix.append(lines[index])
            index += 1
            continue
        break

    end_index, blocks = collect_import_block(lines, index)
    if not blocks:
        return text

    grouped: dict[int, list[tuple[str, str]]] = {0: [], 1: []}
    for block in blocks:
        category, module = import_category(block)
        grouped[category].append((module, block))

    output = prefix[:]
    if output and output[-1].strip() != '':
        output.append('\n')

    wrote_group = False
    for category in (0, 1):
        group = sorted(grouped[category], key=lambda item: (item[0], item[1]))
        if not group:
            continue
        if wrote_group:
            output.append('\n')
        for _, block in group:
            output.append(block if block.endswith('\n') else f'{block}\n')
        wrote_group = True

    remainder = ''.join(lines[end_index:])
    if remainder and not remainder.startswith('\n'):
        output.append('\n')
    return ''.join(output) + remainder


def convert_simple_quotes(text: str) -> str:
    result: list[tokenize.TokenInfo] = []
    stream = io.StringIO(text)

    for token in tokenize.generate_tokens(stream.readline):
        if token.type == tokenize.STRING:
            converted = maybe_convert_string(token.string)
            token = tokenize.TokenInfo(
                token.type,
                converted,
                token.start,
                token.end,
                token.line,
            )
        result.append(token)

    return tokenize.untokenize(result)


def convert_simple_line_quotes(text: str) -> str:
    lines = text.splitlines(keepends=True)
    updated_lines: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('#'):
            updated_lines.append(line)
            continue
        updated_lines.append(
            SIMPLE_QUOTE_PATTERN.sub(lambda match: f"{match.group(1)}'{match.group(2)}'", line)
        )
    return ''.join(updated_lines)


def maybe_convert_string(token_text: str) -> str:
    match = re.match(r'(?i)^([rubf]*)(.*)$', token_text)
    if not match:
        return token_text

    prefix = match.group(1)
    body = match.group(2)
    if not body.startswith('"') or body.startswith('"""'):
        return token_text
    if not body.endswith('"'):
        return token_text

    inner = body[1:-1]
    if "'" in inner or '\\' in inner:
        return token_text
    return f"{prefix}'{inner}'"


def split_top_level_args(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    paren_depth = 0
    bracket_depth = 0
    brace_depth = 0
    quote: str | None = None
    escaped = False

    for character in text:
        current.append(character)
        if quote is not None:
            if escaped:
                escaped = False
                continue
            if character == '\\':
                escaped = True
                continue
            if character == quote:
                quote = None
            continue

        if character in {'\'', '"'}:
            quote = character
            continue
        if character == '(':
            paren_depth += 1
            continue
        if character == ')':
            paren_depth -= 1
            continue
        if character == '[':
            bracket_depth += 1
            continue
        if character == ']':
            bracket_depth -= 1
            continue
        if character == '{':
            brace_depth += 1
            continue
        if character == '}':
            brace_depth -= 1
            continue
        if (
            character == ','
            and paren_depth == 0
            and bracket_depth == 0
            and brace_depth == 0
        ):
            parts.append(''.join(current[:-1]).strip())
            current = []

    tail = ''.join(current).strip()
    if tail:
        parts.append(tail)
    return [part for part in parts if part]


def wrap_call_or_signature(line: str, max_length: int) -> str:
    stripped_newline = line.rstrip('\n')
    if len(stripped_newline) <= max_length:
        return line
    if stripped_newline.lstrip().startswith('#'):
        return line

    open_index = stripped_newline.find('(')
    close_index = stripped_newline.rfind(')')
    if open_index == -1 or close_index == -1 or close_index < open_index:
        return line

    before = stripped_newline[: open_index + 1]
    inside = stripped_newline[open_index + 1 : close_index]
    after = stripped_newline[close_index + 1 :]
    parts = split_top_level_args(inside)
    if len(parts) < 2:
        return line

    indent = len(before) - len(before.lstrip(' '))
    continuation = ' ' * (indent + 4)
    rebuilt = [before.rstrip() + '\n']
    for part in parts:
        rebuilt.append(f'{continuation}{part},\n')
    rebuilt.append(f'{" " * indent}){after}\n')
    return ''.join(rebuilt)


def wrap_comment_line(line: str, max_length: int) -> str:
    stripped_newline = line.rstrip('\n')
    if len(stripped_newline) <= max_length:
        return line

    leading = stripped_newline[: len(stripped_newline) - len(stripped_newline.lstrip(' '))]
    content = stripped_newline[len(leading) :]
    if not content.startswith('# '):
        return line

    wrapped = textwrap.wrap(
        content[2:],
        width=max_length - len(leading) - 2,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if len(wrapped) < 2:
        return line
    return ''.join(f'{leading}# {segment}\n' for segment in wrapped)


def wrap_long_lines(text: str, max_length: int) -> str:
    lines = text.splitlines(keepends=True)
    updated_lines: list[str] = []
    for line in lines:
        line = wrap_comment_line(line, max_length)
        if '\n' in line[:-1]:
            updated_lines.append(line)
            continue
        updated_lines.append(wrap_call_or_signature(line, max_length))
    return ''.join(updated_lines)


def normalize_trailing_newline(text: str) -> str:
    return text.rstrip('\n') + '\n'


def fix_text(text: str, max_length: int) -> str:
    updated = sort_top_imports(text)
    updated = convert_simple_quotes(updated)
    updated = convert_simple_line_quotes(updated)
    updated = wrap_long_lines(updated, max_length)
    updated = normalize_trailing_newline(updated)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Apply common local Python lint fixes for Fabric scripts/tests.'
    )
    parser.add_argument('paths', nargs='+', type=Path)
    parser.add_argument('--max-length', type=int, default=99)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--recursive', action='store_true')
    args = parser.parse_args()

    changed_files: list[Path] = []
    for file_path in iter_python_files(args.paths, args.recursive):
        original = file_path.read_text(encoding='utf-8')
        updated = fix_text(original, args.max_length)
        if updated == original:
            continue
        changed_files.append(file_path)
        if not args.check:
            file_path.write_text(updated, encoding='utf-8')

    for file_path in changed_files:
        print(file_path)

    return 1 if args.check and changed_files else 0


if __name__ == '__main__':
    raise SystemExit(main())