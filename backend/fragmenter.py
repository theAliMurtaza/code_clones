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
import re
import logging
from dataclasses import dataclass, field

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
        logger.warning(f"tree-sitter unavailable ({exc}), using regex fallback")
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


# ── Query strings per language ─────────────────────────────────────────
_QUERIES = {
    "python": "(function_definition) @fn (class_definition) @cls",
    "java":   "(method_declaration)  @fn (class_declaration)  @cls",
}


def _extract_ts(source: str, language: str, filename: str) -> list[Fragment]:
    """Extract fragments using tree-sitter (precise, line-accurate)."""
    lang_obj = _PY_LANG if language == "python" else _JAVA_LANG
    parser   = _make_parser(lang_obj)
    tree     = parser.parse(bytes(source, "utf-8", errors="replace"))
    lines    = source.splitlines()

    query_str = _QUERIES.get(language, "")
    if not query_str:
        return []

    query    = lang_obj.query(query_str)
    captures = query.captures(tree.root_node)

    # tree-sitter 0.24 returns dict[str, list[Node]]
    nodes = []
    if isinstance(captures, dict):
        for node_list in captures.values():
            nodes.extend(node_list)
    else:
        # older format: list of (Node, str)
        nodes = [n for n, _ in captures]

    # De-duplicate by (start_row, end_row)
    seen, fragments = set(), []
    for node in nodes:
        key = (node.start_point[0], node.end_point[0])
        if key in seen or node.end_point[0] - node.start_point[0] < 2:
            continue
        seen.add(key)

        start = node.start_point[0]   # 0-indexed
        end   = node.end_point[0]     # 0-indexed
        code  = "\n".join(lines[start : end + 1])

        # Try to get fragment name from first identifier child
        name = ""
        for child in node.children:
            if child.type in ("identifier", "name"):
                name = source[child.start_byte : child.end_byte]
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


# ── Regex fallback ────────────────────────────────────────────────────
_PY_RE   = re.compile(r"^( {0,8})(async\s+)?def\s+(\w+)", re.MULTILINE)
_JAVA_RE = re.compile(
    r"^( {0,12})(public|private|protected|static|\s)+"
    r"[\w<>\[\]]+\s+(\w+)\s*\(",
    re.MULTILINE,
)


def _extract_regex(source: str, language: str, filename: str) -> list[Fragment]:
    lines   = source.splitlines()
    pattern = _PY_RE if language == "python" else _JAVA_RE
    matches = list(pattern.finditer(source))
    frags   = []
    for i, m in enumerate(matches):
        start = source[:m.start()].count("\n")
        end   = (
            source[:matches[i + 1].start()].count("\n") - 1
            if i + 1 < len(matches)
            else len(lines) - 1
        )
        if end - start < 2:
            continue
        frags.append(Fragment(
            code       = "\n".join(lines[start : end + 1]),
            start_line = start + 1,
            end_line   = end   + 1,
            file       = filename,
            language   = language,
            name       = m.group(3) if m.lastindex and m.lastindex >= 3 else "",
        ))
    return frags


# ── Public API ─────────────────────────────────────────────────────────
def detect_language(filename: str) -> str | None:
    ext = filename.rsplit(".", 1)[-1].lower()
    return {"py": "python", "java": "java"}.get(ext)


def extract_fragments(source: str, filename: str) -> list[Fragment]:
    """
    Main entry point.
    Returns Fragment objects with exact start_line / end_line.
    Uses tree-sitter 0.24 when available, regex otherwise.
    """
    language = detect_language(filename)
    if language is None:
        raise ValueError(f"Unsupported file type: {filename}")

    if _load_tree_sitter():
        try:
            frags = _extract_ts(source, language, filename)
            if frags:
                logger.debug(f"{filename}: {len(frags)} fragments (tree-sitter)")
                return frags
        except Exception as exc:
            logger.warning(f"tree-sitter failed for {filename}: {exc} — using regex")

    frags = _extract_regex(source, language, filename)
    logger.debug(f"{filename}: {len(frags)} fragments (regex fallback)")
    return frags
