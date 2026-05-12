from __future__ import annotations

from dataclasses import replace

from .scenarios import Material, Pulse, Scenario, steam_layer_scenario


def candidate_fuels() -> list[Material]:
    # Отборочные константы, а не квалифицированные материаловедческие данные.
    return [
        Material("UO2", 2.5, 4.2e6, 3120.0),
        Material("UN", 25.0, 4.0e6, 3120.0),
        Material("UC", 60.0, 4.0e6, 2780.0),
        Material("ZrC surrogate", 30.0, 3.6e6, 3570.0),
        Material("HfC surrogate", 22.0, 2.7e6, 4200.0),
        Material("TaC surrogate", 28.0, 5.5e6, 4250.0),
    ]


def candidate_claddings() -> list[Material]:
    return [
        Material("Zircaloy", 18.0, 2.0e6, 2125.0, allowable_temperature_k=1477.0),
        Material("SiC", 12.0, 3.0e6, 3100.0),
        Material("Molybdenum", 90.0, 2.6e6, 2896.0),
        Material("Tantalum", 62.0, 2.8e6, 3290.0),
        # Оптимистический тепловой контрфакт для HfC/W.
        Material("Tungsten", 120.0, 2.6e6, 3695.0),
        Material("ZrC sleeve surrogate", 30.0, 3.6e6, 3570.0),
        Material("TaC sleeve surrogate", 28.0, 5.5e6, 4250.0),
    ]


def make_material_scenario(
    fuel: Material,
    clad: Material,
    pulse_energy_j_per_m: float,
    base: Scenario | None = None,
) -> Scenario:
    scenario = base or steam_layer_scenario()
    return replace(
        scenario,
        name=f"{fuel.name} / {clad.name}",
        fuel=fuel,
        clad=clad,
        pulse=replace(scenario.pulse, energy_j_per_m=pulse_energy_j_per_m),
    )
