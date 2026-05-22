"""Test that src/ is a proper Python package.

Verifies INFRA-09: src/__init__.py must exist so all downstream imports work.
"""
from pathlib import Path


def test_src_is_package():
    """src/__init__.py exists and is a file; src is importable as a package."""
    init_path = Path("src/__init__.py")
    assert init_path.exists(), "src/__init__.py does not exist — src is not a package"
    assert init_path.is_file(), "src/__init__.py is not a regular file"

    # Verify import succeeds
    import src  # noqa: F401
