"""Test that no hardcoded path literals exist in src/*.py (excluding src/config.py).

Verifies INFRA-07: all paths must derive from cfg.DATA_DIR, cfg.OUTPUT_DIR, cfg.DOCS_DIR.
"""
import re
from pathlib import Path


# Regex: quoted literal "data", "outputs", or "docs" as standalone tokens
_HARDCODED_PATH_RE = re.compile(r'["\'](?:data|outputs|docs)["\']')


def test_no_hardcoded_dirs_in_src():
    """Grep src/*.py (excluding config.py) for hardcoded path literals — assert zero matches."""
    src_dir = Path("src")
    violations = []

    for py_file in sorted(src_dir.glob("*.py")):
        if py_file.name == "config.py":
            continue  # config.py is the ONLY place these strings are allowed
        if py_file.name == "__init__.py":
            continue  # empty package marker

        content = py_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), start=1):
            if _HARDCODED_PATH_RE.search(line):
                violations.append(f"{py_file}:{lineno}: {line.strip()}")

    assert violations == [], (
        "Hardcoded path literals found in src/ modules (use cfg.DATA_DIR etc.):\n"
        + "\n".join(violations)
    )
