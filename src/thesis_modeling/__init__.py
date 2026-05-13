"""Переиспользуемые функции расчетных ноутбуков."""

from .cantera_equilibrium import (
    compute_equilibrium_hydrogen,
    compute_python_hydrogen_proxy,
)
from .fallback_physics import simulate_python_fallback
from .genfoam_io import load_genfoam_case
from .scenarios import (
    AnnularWaterLayer,
    Material,
    PinGeometry,
    Pulse,
    Scenario,
    SteamLayer,
    WaterInventory,
    baseline_scenario,
    build_annular_water_scenario,
    build_steam_layer_scenario,
    steam_layer_scenario,
)
from .validation import validate_physical_consistency
from .wall_coupled_water import WallHeatTransfer, apply_wall_coupled_water_model

__all__ = [
    "compute_equilibrium_hydrogen",
    "compute_python_hydrogen_proxy",
    "WallHeatTransfer",
    "apply_wall_coupled_water_model",
    "simulate_python_fallback",
    "load_genfoam_case",
    "AnnularWaterLayer",
    "Material",
    "PinGeometry",
    "Pulse",
    "Scenario",
    "SteamLayer",
    "WaterInventory",
    "baseline_scenario",
    "build_annular_water_scenario",
    "build_steam_layer_scenario",
    "steam_layer_scenario",
    "validate_physical_consistency",
]
