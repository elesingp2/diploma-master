#!/usr/bin/env python3
from __future__ import annotations

import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MPL_CACHE = ROOT / "build" / "matplotlib"
XDG_CACHE = ROOT / "build" / "cache"
MPL_CACHE.mkdir(parents=True, exist_ok=True)
XDG_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))
os.environ.setdefault("XDG_CACHE_HOME", str(XDG_CACHE))

import matplotlib

sys.path.insert(0, str(ROOT / "src"))

matplotlib.use("Agg")

from thesis_modeling.pipeline_export import export_pipeline_artifacts  # noqa: E402
from thesis_modeling.pipeline_v2_export import export_pipeline_v2_artifacts  # noqa: E402


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y"}


def main() -> None:
    allow_all_fallback = _env_flag("ALLOW_PYTHON_FALLBACK")
    export_pipeline_artifacts(
        ROOT / "figures",
        allow_python_fallback=allow_all_fallback or _env_flag("ALLOW_V1_PYTHON_FALLBACK"),
    )
    export_pipeline_v2_artifacts(
        ROOT / "figures",
        allow_python_fallback=allow_all_fallback
        or _env_flag("ALLOW_V2_PYTHON_FALLBACK", default=True),
    )
    print("Wrote pipeline v1/v2 figures and LaTeX reports")


if __name__ == "__main__":
    main()
