"""
Pytest configuration — ensures the workspace root is on sys.path so that
``import src.*`` and ``import utils.*`` work from any test file without
requiring ``PYTHONPATH=.`` to be set manually.
"""
import sys
import os

# Insert the project root (directory containing this file) at the front of
# sys.path if it is not already there.
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)
