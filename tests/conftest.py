"""Root conftest — inject monorepo package paths into sys.path for all test sessions."""
import sys
from pathlib import Path

# Repo root
_ROOT = Path(__file__).parent.parent

# Make every package importable as both `axiom_core` and `packages.axiom_core`
for _pkg_dir in [
    _ROOT / "packages" / "axiom_core",
    _ROOT / "packages" / "axiom_research",
    _ROOT / "packages" / "axiom_graph",
    _ROOT / "packages" / "axiom_providers",
    _ROOT / "packages" / "axiom_contracts",
    _ROOT / "packages",
    _ROOT / "apps",
    _ROOT,
]:
    _p = str(_pkg_dir)
    if _p not in sys.path:
        sys.path.insert(0, _p)
