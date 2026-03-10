#!/usr/bin/env python3
"""Detect internal Python import cycles for selected project paths."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _to_module_name(path: Path) -> str:
    rel = path.relative_to(PROJECT_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _collect_py_files(targets: list[str]) -> list[Path]:
    collected: list[Path] = []
    for target in targets:
        raw = Path(target)
        path = raw if raw.is_absolute() else PROJECT_ROOT / raw
        if not path.exists():
            continue
        if path.is_file() and path.suffix == ".py":
            collected.append(path.resolve())
            continue
        for child in sorted(path.rglob("*.py")):
            if "__pycache__" in child.parts:
                continue
            collected.append(child.resolve())
    return sorted(set(collected))


def _resolve_from_import(module_name: str, imported_module: str | None, level: int) -> str:
    if level <= 0:
        return imported_module or ""
    parts = module_name.split(".")
    if not parts:
        return imported_module or ""
    base = parts[:-level]
    if imported_module:
        base.extend(imported_module.split("."))
    return ".".join(part for part in base if part)


def _find_internal_imports(py_file: Path, module_name: str, modules: set[str]) -> set[str]:
    imports: set[str] = set()
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except Exception:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                raw = alias.name
                candidates = [raw]
                candidates.extend(".".join(raw.split(".")[:i]) for i in range(len(raw.split(".")) - 1, 0, -1))
                for candidate in candidates:
                    if candidate in modules:
                        imports.add(candidate)
                        break
        elif isinstance(node, ast.ImportFrom):
            raw = _resolve_from_import(module_name, node.module, node.level)
            if not raw:
                continue
            candidates = [raw]
            candidates.extend(".".join(raw.split(".")[:i]) for i in range(len(raw.split(".")) - 1, 0, -1))
            for candidate in candidates:
                if candidate in modules:
                    imports.add(candidate)
                    break
    return imports


def _strongly_connected_components(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    components: list[list[str]] = []

    def strongconnect(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for nxt in graph.get(node, set()):
            if nxt not in indices:
                strongconnect(nxt)
                lowlinks[node] = min(lowlinks[node], lowlinks[nxt])
            elif nxt in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[nxt])

        if lowlinks[node] == indices[node]:
            component: list[str] = []
            while stack:
                top = stack.pop()
                on_stack.remove(top)
                component.append(top)
                if top == node:
                    break
            components.append(sorted(component))

    for node in sorted(graph.keys()):
        if node not in indices:
            strongconnect(node)
    return components


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect internal import cycles.")
    parser.add_argument("paths", nargs="+", help="directories/files to scan (e.g. services app.py)")
    args = parser.parse_args()

    py_files = _collect_py_files(args.paths)
    module_map = {_to_module_name(path): path for path in py_files}
    modules = set(module_map.keys())

    graph: dict[str, set[str]] = {}
    for module_name, path in module_map.items():
        imports = _find_internal_imports(path, module_name, modules)
        if module_name in imports:
            # explicit self import is a cycle
            graph[module_name] = {module_name}
        else:
            graph[module_name] = imports

    components = _strongly_connected_components(graph)
    cyclic_components = [
        component
        for component in components
        if len(component) > 1 or (len(component) == 1 and component[0] in graph.get(component[0], set()))
    ]

    if not cyclic_components:
        print("No internal import cycles detected.")
        return 0

    print("Import cycles detected:")
    for idx, component in enumerate(cyclic_components, start=1):
        print(f"{idx}. {' -> '.join(component)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

