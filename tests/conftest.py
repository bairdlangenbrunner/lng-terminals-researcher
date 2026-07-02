"""Make scripts/ importable from the tests (mirrors the scripts' own
sys.path.insert pattern — no install step, per scripts/README.md)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
