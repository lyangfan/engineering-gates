"""Convenience entry point for the repository test suite."""

from __future__ import annotations

import pathlib
import unittest


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parent / "tests"
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.discover(str(root), pattern="test_*.py")
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
