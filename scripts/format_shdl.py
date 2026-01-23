from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from fsc.sexpr import parse, tokenize
except Exception as exc:  # pragma: no cover - local tooling
    raise SystemExit(f"Failed to import SHDL parser: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Format SHDL files with 4-space indents")
    parser.add_argument("paths", nargs="+", help="Files or directories")
    parser.add_argument("--check", action="store_true", help="Exit non-zero if changes needed")
    args = parser.parse_args()

    files = _collect_files(args.paths)
    changed = 0
    for path in files:
        text = path.read_text()
        formatted = format_shdl(text)
        if formatted != text:
            changed += 1
            if args.check:
                continue
            path.write_text(formatted)
    if args.check and changed:
        raise SystemExit(1)


def _collect_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.shdl")))
        else:
            files.append(path)
    return files


def format_shdl(text: str) -> str:
    exprs = parse(tokenize(text))
    if len(exprs) != 1:
        raise ValueError("Expected exactly one top-level form")
    rendered = _render(exprs[0], indent=0)
    return rendered + "\n"


def _render(expr: object, indent: int) -> str:
    if isinstance(expr, str):
        return expr
    if not isinstance(expr, list):
        raise ValueError("Invalid s-expr node")
    if not expr:
        return "()"

    if _can_inline(expr):
        inner = " ".join(_render(item, 0) for item in expr)
        return f"({inner})"

    head = _render(expr[0], 0)
    lines = ["(" + head]
    if expr[0] == "ports":
        lines.extend(_render_ports(expr[1:], indent + 4))
    elif expr[0] == "module":
        items = expr[1:]
        if len(expr) >= 2 and isinstance(expr[1], str):
            lines[0] = f"(module {expr[1]}"
            items = expr[2:]
        for item in items:
            lines.append(" " * (indent + 4) + _render(item, indent + 4))
            if _is_ports_form(item):
                lines.append("")
    else:
        for item in expr[1:]:
            lines.append(" " * (indent + 4) + _render(item, indent + 4))
    lines[-1] += ")"
    return "\n".join(lines)


def _can_inline(expr: list) -> bool:
    if all(isinstance(item, str) for item in expr):
        return True
    if not expr:
        return True
    return False


def _render_ports(items: list, indent: int) -> list[str]:
    ins: list[str] = []
    outs: list[str] = []
    for item in items:
        if not isinstance(item, list) or len(item) != 2:
            rendered = _render(item, indent)
            ins.append(" " * indent + rendered)
            continue
        direction, name = item
        if direction == "out":
            outs.append(" " * indent + f"({direction} {name})")
        else:
            ins.append(" " * indent + f"({direction} {name})")
    lines = ins
    if ins and outs:
        lines.append("")
    lines.extend(outs)
    return lines


def _is_ports_form(expr: object) -> bool:
    return isinstance(expr, list) and expr and expr[0] == "ports"


if __name__ == "__main__":
    main()
