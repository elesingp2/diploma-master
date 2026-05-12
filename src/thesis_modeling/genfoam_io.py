from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .genfoam_post import canonicalize_thermal_series
from .scenarios import Scenario


DEFAULT_THERMAL_SERIES_NAME = "thermal_timeseries.csv"


def load_genfoam_case(
    case_path: str | Path,
    scenario: Scenario,
    *,
    series_name: str = DEFAULT_THERMAL_SERIES_NAME,
) -> dict[str, Any]:
    """Читает тепловой ряд GeN-Foam без локального пересчета физики."""
    series_path = _resolve_series_path(Path(case_path), series_name)
    if series_path.suffix == ".npz":
        columns = _read_npz_columns(series_path)
    else:
        columns = _read_csv_columns(series_path)
    return canonicalize_thermal_series(
        columns,
        scenario,
        source="genfoam",
        provenance=series_path,
    )


def _resolve_series_path(case_path: Path, series_name: str) -> Path:
    if case_path.is_file():
        return case_path
    if not case_path.exists():
        raise FileNotFoundError(
            f"Путь к кейсу GeN-Foam не найден: {case_path}. "
            f"Нужен файл или каталог с {series_name}."
        )

    candidates = [
        case_path / series_name,
        case_path / "postProcessing" / series_name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Не найден тепловой ряд GeN-Foam {series_name!r} внутри {case_path}."
    )


def _read_csv_columns(path: Path) -> dict[str, np.ndarray]:
    table = np.genfromtxt(
        path,
        delimiter=",",
        names=True,
        dtype=float,
        encoding="utf-8",
    )
    if table.dtype.names is None:
        raise ValueError(f"В CSV GeN-Foam нет строки заголовка: {path}.")
    return {
        name: np.atleast_1d(np.asarray(table[name], dtype=float))
        for name in table.dtype.names
    }


def _read_npz_columns(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as data:
        return {name: np.asarray(data[name], dtype=float) for name in data.files}
