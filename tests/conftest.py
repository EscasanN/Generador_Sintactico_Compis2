"""Opt-in acceptance mode: MARS integrations may never silently skip."""
import pytest


def pytest_addoption(parser):
    parser.addoption('--require-mars', action='store_true', help='Fail if MARS is unavailable')


@pytest.fixture(scope='session')
def mars(request):
    import os
    from pathlib import Path
    from src.mips.models import MarsConfig
    configured = os.environ.get('MARS_JAR')
    path = Path(configured) if configured else Path('output/mips/tools/Mars4_5.jar')
    if not path.is_file():
        if request.config.getoption('--require-mars'):
            pytest.fail('MARS_JAR must identify MARS 4.5 for acceptance')
        pytest.skip('MARS unavailable; use --require-mars for acceptance')
    return MarsConfig(path.resolve())
