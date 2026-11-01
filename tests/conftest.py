"""Temporales dentro del workspace, también bajo sandbox Windows."""
from pathlib import Path
from uuid import uuid4


def pytest_configure(config):
    root = Path(__file__).resolve().parents[1] / 'tmp'
    root.mkdir(exist_ok=True)
    if not config.option.basetemp:
        config.option.basetemp = str(root / ('pytest-' + uuid4().hex))
