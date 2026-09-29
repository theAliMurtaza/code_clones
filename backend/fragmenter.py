"""
fragmenter.py
Splits source code into meaningful fragments (functions, methods, classes)
using tree-sitter 0.24.x with per-language grammar packages.

Compatible with:
  tree-sitter       == 0.24.0
  tree-sitter-python == 0.23.6
  tree-sitter-java   == 0.23.5
  Python             >= 3.12

No .so binary file is needed — language grammars are bundled
inside the tree-sitter-python / tree-sitter-java pip packages.
"""

from __future__ import annotations
import ast
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Fragment:
    """A single extractable code unit with its exact line range."""
    code:       str
    start_line: int           # 1-indexed, inclusive
    end_line:   int           # 1-indexed, inclusive
    file:       str = ""
    language:   str = ""
    name:       str = ""

    @property
    def line_range(self) -> list[int]:
        return list(range(self.start_line, self.end_line + 1))

    @property
    def num_lines(self) -> int:
        return self.end_line - self.start_line + 1


# ── Lazy tree-sitter loader ───────────────────────────────────────────
_ts_available = False
_PY_LANG      = None
_JAVA_LANG    = None


def _load_tree_sitter() -> bool:
    global _ts_available, _PY_LANG, _JAVA_LANG
    if _ts_available:
        return True
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_python as tsp
        import tree_sitter_java  as tsj

        _PY_LANG   = Language(tsp.language())
        _JAVA_LANG = Language(tsj.language())
        _ts_available = True
        logger.info("tree-sitter 0.24 loaded (Python + Java grammars ready)")
        return True
    except Exception as exc:
        logger.warning(f"tree-sitter unavailable ({exc}), using source blocks")
        return False


def _make_parser(lang_obj):
    """Create a Parser object, compatible with tree-sitter 0.22 – 0.25."""
    from tree_sitter import Parser
    try:
        # tree-sitter >= 0.22: Parser accepts language in constructor
        return Parser(lang_obj)
    except TypeError:
        # tree-sitter 0.20 / 0.21: use set_language()
        p = Parser()
        p.set_language(lang_obj)
        return p


def _extract_ts(source: str, language: str, filename: str) -> list[Fragment]:
    """Extract fragments using tree-sitter (precise, line-accurate)."""
    lang_obj = _PY_LANG if language == "python" else _JAVA_LANG
    parser   = _make_parser(lang_obj)
    tree     = parser.parse(bytes(source, "utf-8", errors="replace"))
    lines    = source.splitlines()

    # Walking nodes avoids the incompatible Query APIs in tree-sitter releases.
    wanted = {"function_definition", "method_declaration", "constructor_declaration"}
    nodes, pending = [], [tree.root_node]
    while pending:
        node = pending.pop()
        if node.type in wanted:
            nodes.append(node)
        pending.extend(reversed(node.children))

    # De-duplicate by (start_row, end_row)
    seen, fragments = set(), []
    for node in nodes:
        key = (node.start_point[0], node.end_point[0])
        if key in seen:
            continue
        seen.add(key)

        start = node.start_point[0]   # 0-indexed
        end   = node.end_point[0]     # 0-indexed
        code  = "\n".join(lines[start : end + 1])

        # Try to get fragment name from first identifier child
        name = ""
        for child in node.children:
            if child.type in ("identifier", "name"):
                name = source.encode("utf-8")[child.start_byte : child.end_byte].decode("utf-8")
                break

        fragments.append(Fragment(
            code       = code,
            start_line = start + 1,   # convert to 1-indexed
            end_line   = end   + 1,
            file       = filename,
            language   = language,
            name       = name,
        ))

    return fragments


# ── Public API ─────────────────────────────────────────────────────────
def detect_language(filename: str) -> str | None:
    ext = filename.rsplit(".", 1)[-1].lower()
    return {"py": "python", "java": "java"}.get(ext)


def extract_fragments(source: str, filename: str) -> list[Fragment]:
    """
    Main entry point.
    Returns Fragment objects with exact start_line / end_line.
    Uses Python AST or Java tree-sitter, plus source blocks covering all other code.
    """
    language = detect_language(filename)
    if language is None:
        raise ValueError(f"Unsupported file type: {filename}")

    frags = []
    if language == "python":
        try:
            tree = ast.parse(source)
            lines = source.splitlines()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    start = min([node.lineno] + [d.lineno for d in node.decorator_list])
                    frags.append(Fragment("\n".join(lines[start - 1:node.end_lineno]),
                                          start, node.end_lineno, filename, language, node.name))
        except SyntaxError:
            pass
    elif _load_tree_sitter():
        try:
            frags = _extract_ts(source, language, filename)
        except Exception as exc:
            logger.warning(f"tree-sitter failed for {filename}: {exc} — using source blocks")

    # Include top-level statements, fields and scripts outside extracted functions.
    # Preserve blank lines and indentation so displayed lines address the original file.
    lines = source.splitlines()
    covered = {n for frag in frags for n in frag.line_range}
    start = None
    for n in range(1, len(lines) + 2):
        if n <= len(lines) and n not in covered:
            if start is None:
                start = n
        elif start is not None:
            code = "\n".join(lines[start - 1:n - 1])
            if code.strip():
                frags.append(Fragment(code, start, n - 1, filename, language))
            start = None

    # Bound long units so code past a model's input limit also gets compared.
    chunks = {}
    for frag in frags:
        fragment_lines = frag.code.splitlines()
        for offset in range(0, len(fragment_lines), 60):
            chunk = fragment_lines[offset:offset + 80]
            first = frag.start_line + offset
            last = first + len(chunk) - 1
            chunks[(first, last)] = Fragment("\n".join(chunk), first, last,
                                             filename, language, frag.name)
            if offset + 80 >= len(fragment_lines):
                break
    return [chunks[key] for key in sorted(chunks)]
