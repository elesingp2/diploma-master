from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Any, TypedDict

import numpy as np

from .scenarios import Scenario

M_H2_KG_PER_MOL = 2.01588e-3
M_H2O_KG_PER_MOL = 18.01528e-3


class CanteraUnavailableError(RuntimeError):
    """Ошибка настройки, если Cantera недоступна в текущем окружении."""


class CanteraHydrogenResult(TypedDict):
    method: str
    uses_cantera: bool
    mechanism: str
    threshold_k: float
    hydrogen_kg_per_m: np.ndarray
    max_hydrogen_kg_per_m: np.ndarray
    h2_mole_fraction: np.ndarray
    equilibrium_temperature_k: np.ndarray
    pressure_pa: np.ndarray
    peak_hydrogen_g_per_m: float
    peak_water_temperature_k: float
    peak_h2_mole_fraction: float
    note: str


def compute_equilibrium_hydrogen(
    result: dict[str, Any],
    scenario: Scenario,
    *,
    mechanism: str = "gri30.yaml",
) -> CanteraHydrogenResult:
    """Считает равновесный H2 по тепловому состоянию, выгруженному из GeN-Foam."""
    ct = _import_cantera()
    gas = ct.Solution(mechanism)
    _require_species(gas, ("H2O", "H2"))

    temperature_k = np.asarray(result["water_temperature_k"], dtype=float)
    steam_mass_kg_per_m = np.asarray(result["steam_mass_kg_per_m"], dtype=float)
    pressure_pa = _pressure_series(result, scenario, temperature_k.size)

    h2_mole_fraction = np.zeros_like(temperature_k, dtype=float)
    hydrogen_kg_per_m = np.zeros_like(temperature_k, dtype=float)
    max_hydrogen_kg_per_m = steam_mass_kg_per_m * M_H2_KG_PER_MOL / M_H2O_KG_PER_MOL

    for index, (temperature, pressure, steam_mass) in enumerate(
        zip(temperature_k, pressure_pa, steam_mass_kg_per_m, strict=True)
    ):
        if steam_mass <= 0.0:
            continue
        gas.TPX = float(temperature), float(pressure), "H2O:1"
        gas.equilibrate("TP")
        x_h2 = float(gas["H2"].X[0])
        h2_mole_fraction[index] = x_h2
        hydrogen_kg_per_m[index] = (
            steam_mass
            / M_H2O_KG_PER_MOL
            * _h2_moles_per_initial_h2o_mole(gas, x_h2)
            * M_H2_KG_PER_MOL
        )

    hydrogen_kg_per_m = np.minimum(hydrogen_kg_per_m, max_hydrogen_kg_per_m)
    return {
        "method": "cantera_equilibrium_tp",
        "uses_cantera": True,
        "mechanism": mechanism,
        "threshold_k": scenario.chemistry_threshold_k,
        "hydrogen_kg_per_m": hydrogen_kg_per_m,
        "max_hydrogen_kg_per_m": max_hydrogen_kg_per_m,
        "h2_mole_fraction": h2_mole_fraction,
        "equilibrium_temperature_k": temperature_k,
        "pressure_pa": pressure_pa,
        "peak_hydrogen_g_per_m": float(np.max(hydrogen_kg_per_m) * 1e3),
        "peak_water_temperature_k": float(np.max(temperature_k)),
        "peak_h2_mole_fraction": float(np.max(h2_mole_fraction)),
        "note": "Cantera TP equilibrium for steam; recombination and product separation are not modeled.",
    }


def compute_python_hydrogen_proxy(
    result: dict[str, Any],
    scenario: Scenario,
) -> CanteraHydrogenResult:
    """Считает пороговую оценку H2 без Cantera."""
    temperature_k = np.asarray(result["water_temperature_k"], dtype=float)
    steam_mass_kg_per_m = np.asarray(result["steam_mass_kg_per_m"], dtype=float)
    pressure_pa = _pressure_series(result, scenario, temperature_k.size)
    excess_k = np.maximum(temperature_k - scenario.chemistry_threshold_k, 0.0)

    # Оценка не заменяет равновесную термодинамику: доля H2 монотонно растет
    # выше температурного ориентира и ограничена стехиометрией воды.
    dissociation_fraction = 0.10 * (1.0 - np.exp(-excess_k / 650.0))
    dissociation_fraction = np.clip(dissociation_fraction, 0.0, 0.10)
    h2_mole_fraction = dissociation_fraction / (1.0 + 0.5 * dissociation_fraction)
    hydrogen_kg_per_m = (
        steam_mass_kg_per_m
        / M_H2O_KG_PER_MOL
        * dissociation_fraction
        * M_H2_KG_PER_MOL
    )
    max_hydrogen_kg_per_m = steam_mass_kg_per_m * M_H2_KG_PER_MOL / M_H2O_KG_PER_MOL
    hydrogen_kg_per_m = np.minimum(hydrogen_kg_per_m, max_hydrogen_kg_per_m)
    return {
        "method": "python_threshold_proxy",
        "uses_cantera": False,
        "mechanism": "none",
        "threshold_k": scenario.chemistry_threshold_k,
        "hydrogen_kg_per_m": hydrogen_kg_per_m,
        "max_hydrogen_kg_per_m": max_hydrogen_kg_per_m,
        "h2_mole_fraction": h2_mole_fraction,
        "equilibrium_temperature_k": temperature_k,
        "pressure_pa": pressure_pa,
        "peak_hydrogen_g_per_m": float(np.max(hydrogen_kg_per_m) * 1e3),
        "peak_water_temperature_k": float(np.max(temperature_k)),
        "peak_h2_mole_fraction": float(np.max(h2_mole_fraction)),
        "note": "Расчет без Cantera: пороговая монотонная оценка, не равновесная термодинамика.",
    }


def _import_cantera():
    try:
        import cantera as ct
    except ModuleNotFoundError as exc:
        raise CanteraUnavailableError(
            "Cantera не установлена. Установите пакет с extra 'chemistry' "
            "или добавьте Cantera в активное Python-окружение."
        ) from exc
    _register_cantera_data_dir(ct)
    return ct


def _register_cantera_data_dir(ct: Any) -> None:
    data_dir = Path(ct.__file__).resolve().parent / "data"
    if not data_dir.is_dir() or not hasattr(ct, "add_directory"):
        return

    # Cantera 3.2 на macOS некорректно режет пути с кириллицей в каталоге
    # проекта, поэтому регистрируем короткую ASCII-ссылку на штатный data-dir.
    env_data = os.environ.get("THESIS_CANTERA_DATA")
    link_dir = (
        Path(env_data)
        if env_data
        else Path(tempfile.gettempdir()) / "thesis_cantera_data"
    )
    try:
        if link_dir.exists() and link_dir.resolve() != data_dir:
            if link_dir.is_symlink():
                link_dir.unlink()
            else:
                link_dir = Path(tempfile.gettempdir()) / f"thesis_cantera_data_{os.getpid()}"
        if not link_dir.exists():
            link_dir.symlink_to(data_dir, target_is_directory=True)
        ct.add_directory(str(link_dir))
    except OSError:
        ct.add_directory(str(data_dir))


def _require_species(gas, names: tuple[str, ...]) -> None:
    missing = [name for name in names if name not in gas.species_names]
    if missing:
        raise ValueError(
            "В механизме Cantera нет нужных частиц: " + ", ".join(missing)
        )


def _pressure_series(
    result: dict[str, Any],
    scenario: Scenario,
    n_points: int,
) -> np.ndarray:
    if "pressure_pa" in result:
        pressure = np.asarray(result["pressure_pa"], dtype=float)
        if pressure.size != n_points:
            raise ValueError(
                f"В pressure_pa {pressure.size} строк, ожидалось {n_points}."
            )
        return pressure
    return np.full(n_points, scenario.water.pressure_pa, dtype=float)


def _h2_moles_per_initial_h2o_mole(gas, x_h2: float) -> float:
    hydrogen_atoms_per_equilibrium_mole = 0.0
    for species_name, mole_fraction in zip(
        gas.species_names,
        gas.X,
        strict=True,
    ):
        if mole_fraction == 0.0:
            continue
        hydrogen_atoms_per_equilibrium_mole += mole_fraction * gas.n_atoms(
            species_name,
            "H",
        )
    if hydrogen_atoms_per_equilibrium_mole <= 0.0:
        return 0.0
    total_equilibrium_moles_per_initial_h2o_mole = (
        2.0 / hydrogen_atoms_per_equilibrium_mole
    )
    return x_h2 * total_equilibrium_moles_per_initial_h2o_mole
