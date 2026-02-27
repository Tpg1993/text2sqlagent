"""
conftest.py — Shared pytest fixtures for the evaluation suite.

All eval scripts in this package can use these fixtures.
Fixtures here:
    - backend_root    : Path to backend root directory
    - env_loaded      : Ensures .env is loaded before any test
    - reports_dir     : Ensures the reports/ directory exists
"""
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Ensure backend root is on sys.path for all eval tests
# ---------------------------------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def env_loaded():
    """
    Session-scoped fixture that loads the .env file once before any tests run.
    This ensures all app modules receive their configuration on import.
    """
    env_file = BACKEND_ROOT / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        pytest.warns(
            UserWarning,
            match=".env file not found",
        )


@pytest.fixture(scope="session")
def backend_root() -> Path:
    """Returns the absolute path to the backend root directory."""
    return BACKEND_ROOT


@pytest.fixture(scope="session")
def datasets_dir(backend_root: Path) -> Path:
    """Returns the path to the evaluation datasets directory."""
    path = backend_root / "evaluation" / "datasets"
    assert path.exists(), f"Datasets directory not found: {path}"
    return path


@pytest.fixture(scope="session")
def reports_dir(backend_root: Path) -> Path:
    """Creates and returns the path to the evaluation reports directory."""
    path = backend_root / "evaluation" / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path
