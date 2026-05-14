from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from thesis_modeling.genfoam_io import load_genfoam_case  # noqa: E402
from thesis_modeling.scenarios import (  # noqa: E402
    WaterInventory,
    build_steam_layer_scenario,
)
from thesis_modeling.validation import validate_physical_consistency  # noqa: E402
from thesis_modeling.water_state import (  # noqa: E402
    water_energy_for_temperature_j_per_m,
    water_state_from_energy,
)


class WaterStateTests(unittest.TestCase):
    def test_energy_temperature_round_trip_for_superheated_steam(self) -> None:
        water = WaterInventory(
            mass_kg_per_m=1.0e-3,
            initial_temperature_k=620.0,
            saturation_temperature_k=620.0,
            latent_heat_j_kg=1.10e6,
            cp_vapor_j_kg_k=2.6e3,
        )

        energy_j_per_m = water_energy_for_temperature_j_per_m(1200.0, water)
        state = water_state_from_energy(energy_j_per_m, water)

        self.assertEqual(state.phase, "steam_superheating")
        self.assertTrue(math.isclose(state.temperature_k, 1200.0, rel_tol=1e-12))
        self.assertTrue(math.isclose(state.vapor_quality, 1.0, rel_tol=1e-12))


class GenFoamSeriesTests(unittest.TestCase):
    def test_reference_series_has_valid_pipeline_contract(self) -> None:
        scenario = build_steam_layer_scenario(
            genfoam_case_path="data/genfoam/near_wall_steam_layer",
        )

        result = load_genfoam_case(
            ROOT / "data/genfoam/near_wall_steam_layer",
            scenario,
        )
        validation = validate_physical_consistency(result)

        self.assertTrue(validation["ok"])
        self.assertEqual(result["thermal_source"], "genfoam")
        self.assertTrue(np.all(np.diff(result["time_s"]) > 0.0))
        self.assertGreater(float(np.max(result["water_temperature_k"])), 670.0)
        self.assertLess(float(np.max(result["water_temperature_k"])), 700.0)
        self.assertGreaterEqual(float(np.min(result["water_energy_j_per_m"])), 0.0)


if __name__ == "__main__":
    unittest.main()
