from __future__ import annotations

from dataclasses import dataclass
import math


STEAM_GAS_CONSTANT_J_KG_K = 461.5


@dataclass(frozen=True)
class Material:
    name: str
    conductivity_w_m_k: float
    volumetric_heat_capacity_j_m3_k: float
    melting_temperature_k: float
    allowable_temperature_k: float | None = None

    @property
    def limit_temperature_k(self) -> float:
        return (
            self.allowable_temperature_k
            if self.allowable_temperature_k is not None
            else self.melting_temperature_k
        )


@dataclass(frozen=True)
class PinGeometry:
    fuel_radius_m: float = 4.00e-3
    gap_outer_radius_m: float = 4.08e-3
    clad_outer_radius_m: float = 4.68e-3
    length_m: float = 1.0
    n_fuel: int = 32
    n_clad: int = 10


@dataclass(frozen=True)
class Pulse:
    energy_j_per_m: float = 2.5e5
    duration_s: float = 0.20
    shape: str = "square"


@dataclass(frozen=True)
class WaterInventory:
    mass_kg_per_m: float = 6.0e-2
    initial_temperature_k: float = 580.0
    saturation_temperature_k: float = 620.0
    pressure_pa: float = 15.5e6
    heat_transfer_coefficient_w_m2_k: float = 3.0e4
    cp_liquid_j_kg_k: float = 5.2e3
    latent_heat_j_kg: float = 1.55e6
    cp_vapor_j_kg_k: float = 2.6e3


@dataclass(frozen=True)
class SteamLayer:
    thickness_m: float = 1.0e-4
    pressure_pa: float = 15.5e6
    initial_temperature_k: float = 620.0
    heat_transfer_coefficient_w_m2_k: float = 5.0e3
    cp_vapor_j_kg_k: float = 2.6e3


@dataclass(frozen=True)
class AnnularWaterLayer:
    thickness_m: float = 1.0e-4
    pressure_pa: float = 15.5e6
    initial_temperature_k: float = 620.0
    saturation_temperature_k: float = 620.0
    liquid_density_kg_m3: float = 650.0
    cp_liquid_j_kg_k: float = 6.0e3
    latent_heat_j_kg: float = 1.10e6
    cp_vapor_j_kg_k: float = 2.6e3
    wall_temperature_cap: bool = True


@dataclass(frozen=True)
class Scenario:
    name: str
    geometry: PinGeometry
    fuel: Material
    clad: Material
    water: WaterInventory
    pulse: Pulse
    gap_conductance_w_m2_k: float = 5.0e3
    initial_solid_temperature_k: float = 580.0
    t_end_s: float = 20.0
    chemistry_threshold_k: float = 3273.15
    steam_layer: SteamLayer | None = None
    annular_water_layer: AnnularWaterLayer | None = None
    genfoam_case_path: str | None = None


DEFAULT_FUEL = Material(
    name="UO2",
    conductivity_w_m_k=3.5,
    volumetric_heat_capacity_j_m3_k=3.0e6,
    melting_temperature_k=3120.0,
)
DEFAULT_CLAD = Material(
    name="Zircaloy",
    conductivity_w_m_k=18.0,
    volumetric_heat_capacity_j_m3_k=2.0e6,
    melting_temperature_k=2125.0,
    allowable_temperature_k=1477.0,
)


def baseline_scenario() -> Scenario:
    return Scenario(
        name="baseline_pulse",
        geometry=PinGeometry(),
        fuel=DEFAULT_FUEL,
        clad=DEFAULT_CLAD,
        water=WaterInventory(),
        pulse=Pulse(),
    )


def steam_layer_mass_kg_per_m(geometry: PinGeometry, layer: SteamLayer) -> float:
    if layer.thickness_m <= 0.0:
        raise ValueError("Steam layer thickness must be positive.")
    if layer.initial_temperature_k <= 0.0:
        raise ValueError("Steam layer temperature must be positive.")
    outer_radius = geometry.clad_outer_radius_m + layer.thickness_m
    volume_m3_per_m = math.pi * (outer_radius**2 - geometry.clad_outer_radius_m**2)
    density_kg_m3 = (
        layer.pressure_pa
        / (STEAM_GAS_CONSTANT_J_KG_K * layer.initial_temperature_k)
    )
    return density_kg_m3 * volume_m3_per_m


def annular_water_mass_kg_per_m(
    geometry: PinGeometry,
    layer: AnnularWaterLayer,
) -> float:
    if layer.thickness_m <= 0.0:
        raise ValueError("Annular water layer thickness must be positive.")
    if layer.liquid_density_kg_m3 <= 0.0:
        raise ValueError("Liquid water density must be positive.")
    outer_radius = geometry.clad_outer_radius_m + layer.thickness_m
    volume_m3_per_m = math.pi * (outer_radius**2 - geometry.clad_outer_radius_m**2)
    return layer.liquid_density_kg_m3 * volume_m3_per_m


def build_steam_layer_scenario(
    *,
    geometry: PinGeometry | None = None,
    fuel: Material = DEFAULT_FUEL,
    clad: Material = DEFAULT_CLAD,
    pulse: Pulse | None = None,
    steam_layer: SteamLayer | None = None,
    gap_conductance_w_m2_k: float = 5.0e3,
    t_end_s: float = 20.0,
    chemistry_threshold_k: float = 3273.15,
    genfoam_case_path: str | None = None,
    name: str = "near_wall_steam_layer",
) -> Scenario:
    geometry = geometry or PinGeometry()
    layer = steam_layer or SteamLayer()
    layer_mass = steam_layer_mass_kg_per_m(geometry, layer)
    return Scenario(
        name=name,
        geometry=geometry,
        fuel=fuel,
        clad=clad,
        water=WaterInventory(
            mass_kg_per_m=layer_mass,
            initial_temperature_k=layer.initial_temperature_k,
            saturation_temperature_k=layer.initial_temperature_k,
            pressure_pa=layer.pressure_pa,
            heat_transfer_coefficient_w_m2_k=layer.heat_transfer_coefficient_w_m2_k,
            cp_liquid_j_kg_k=layer.cp_vapor_j_kg_k,
            latent_heat_j_kg=0.0,
            cp_vapor_j_kg_k=layer.cp_vapor_j_kg_k,
        ),
        pulse=pulse or Pulse(),
        gap_conductance_w_m2_k=gap_conductance_w_m2_k,
        initial_solid_temperature_k=layer.initial_temperature_k,
        t_end_s=t_end_s,
        chemistry_threshold_k=chemistry_threshold_k,
        steam_layer=layer,
        genfoam_case_path=genfoam_case_path,
    )


def build_annular_water_scenario(
    *,
    geometry: PinGeometry | None = None,
    fuel: Material = DEFAULT_FUEL,
    clad: Material = DEFAULT_CLAD,
    pulse: Pulse | None = None,
    annular_water_layer: AnnularWaterLayer | None = None,
    gap_conductance_w_m2_k: float = 5.0e3,
    t_end_s: float = 20.0,
    chemistry_threshold_k: float = 3273.15,
    genfoam_case_path: str | None = None,
    name: str = "annular_water_thermolysis",
) -> Scenario:
    geometry = geometry or PinGeometry()
    layer = annular_water_layer or AnnularWaterLayer()
    layer_mass = annular_water_mass_kg_per_m(geometry, layer)
    return Scenario(
        name=name,
        geometry=geometry,
        fuel=fuel,
        clad=clad,
        water=WaterInventory(
            mass_kg_per_m=layer_mass,
            initial_temperature_k=layer.initial_temperature_k,
            saturation_temperature_k=layer.saturation_temperature_k,
            pressure_pa=layer.pressure_pa,
            cp_liquid_j_kg_k=layer.cp_liquid_j_kg_k,
            latent_heat_j_kg=layer.latent_heat_j_kg,
            cp_vapor_j_kg_k=layer.cp_vapor_j_kg_k,
        ),
        pulse=pulse or Pulse(),
        gap_conductance_w_m2_k=gap_conductance_w_m2_k,
        initial_solid_temperature_k=layer.initial_temperature_k,
        t_end_s=t_end_s,
        chemistry_threshold_k=chemistry_threshold_k,
        annular_water_layer=layer,
        genfoam_case_path=genfoam_case_path,
    )


def steam_layer_scenario() -> Scenario:
    return build_steam_layer_scenario()


def scenario_summary(scenario: Scenario) -> dict[str, float | str]:
    geometry = scenario.geometry
    water = scenario.water
    summary: dict[str, float | str] = {
        "name": scenario.name,
        "fuel_radius_mm": geometry.fuel_radius_m * 1e3,
        "gap_thickness_um": (geometry.gap_outer_radius_m - geometry.fuel_radius_m)
        * 1e6,
        "clad_thickness_mm": (geometry.clad_outer_radius_m - geometry.gap_outer_radius_m)
        * 1e3,
        "pulse_energy_kj_per_m": scenario.pulse.energy_j_per_m / 1e3,
        "pulse_duration_s": scenario.pulse.duration_s,
        "water_mass_g_per_m": water.mass_kg_per_m * 1e3,
        "water_initial_temperature_k": water.initial_temperature_k,
        "water_saturation_temperature_k": water.saturation_temperature_k,
        "chemistry_threshold_k": scenario.chemistry_threshold_k,
        "fuel_melting_temperature_k": scenario.fuel.melting_temperature_k,
        "clad_melting_temperature_k": scenario.clad.melting_temperature_k,
        "clad_limit_temperature_k": scenario.clad.limit_temperature_k,
    }
    if scenario.genfoam_case_path is not None:
        summary["genfoam_case_path"] = scenario.genfoam_case_path
    if scenario.steam_layer is not None:
        summary.update(
            {
                "steam_layer_thickness_um": scenario.steam_layer.thickness_m * 1e6,
                "steam_layer_mass_g_per_m": water.mass_kg_per_m * 1e3,
                "steam_layer_pressure_mpa": scenario.steam_layer.pressure_pa / 1e6,
            }
        )
    if scenario.annular_water_layer is not None:
        summary.update(
            {
                "water_layer_thickness_um": scenario.annular_water_layer.thickness_m
                * 1e6,
                "water_layer_mass_g_per_m": water.mass_kg_per_m * 1e3,
                "water_layer_pressure_mpa": scenario.annular_water_layer.pressure_pa
                / 1e6,
            }
        )
    return summary
