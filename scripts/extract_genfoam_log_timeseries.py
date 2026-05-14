#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


TIME_RE = re.compile(r"^Time\s*=\s*([0-9Ee.+-]+)")
PIN_RE = re.compile(
    r"^T\.nuclearFuelPin\.(fuel|clad)\s+\(avg min max\)\s*=\s*"
    r"([0-9Ee.+-]+)\s+([0-9Ee.+-]+)\s+([0-9Ee.+-]+)\s+K"
)
FLUID_RE = re.compile(
    r"^T\s+\(avg min max\)\s*=\s*"
    r"([0-9Ee.+-]+)\s+([0-9Ee.+-]+)\s+([0-9Ee.+-]+)\s+K"
)
POWER_RE = re.compile(r"^Total power in nuclearFuelPin\s*=\s*([0-9Ee.+-]+)\s+W")


def parse_log(path: Path) -> list[dict[str, float]]:
    """Извлекает последние температуры GeN-Foam для каждого расчетного времени."""
    rows: list[dict[str, float]] = []
    current: dict[str, float] | None = None

    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        time_match = TIME_RE.match(line)
        if time_match:
            _append_if_complete(rows, current)
            current = {"time_s": float(time_match.group(1))}
            continue
        if current is None:
            continue

        pin_match = PIN_RE.match(line)
        if pin_match:
            prefix = "fuel" if pin_match.group(1) == "fuel" else "clad"
            current[f"{prefix}_average_k"] = float(pin_match.group(2))
            current[f"{prefix}_minimum_k"] = float(pin_match.group(3))
            current[f"{prefix}_maximum_k"] = float(pin_match.group(4))
            continue

        fluid_match = FLUID_RE.match(line)
        if fluid_match:
            current["fluid_average_k"] = float(fluid_match.group(1))
            current["fluid_minimum_k"] = float(fluid_match.group(2))
            current["fluid_maximum_k"] = float(fluid_match.group(3))
            continue

        power_match = POWER_RE.match(line)
        if power_match:
            current["genfoam_total_power_w"] = float(power_match.group(1))

    _append_if_complete(rows, current)
    if len(rows) < 2:
        raise ValueError(f"В логе {path} меньше двух полных временных срезов.")
    t0 = rows[0]["time_s"]
    for row in rows:
        row["time_s"] = row["time_s"] - t0
    return rows


def write_timeseries(rows: list[dict[str, float]], output: Path, pressure_pa: float) -> None:
    """Пишет ряд в контракт, который читают notebooks и LaTeX-экспорт."""
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "time_s",
        "fuel_center_k",
        "fuel_average_k",
        "fuel_surface_k",
        "clad_inner_k",
        "clad_outer_k",
        "water_temperature_k",
        "pressure_pa",
        "genfoam_total_power_w",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            clad_max = row["clad_maximum_k"]
            writer.writerow(
                {
                    "time_s": f"{row['time_s']:.8g}",
                    "fuel_center_k": f"{row['fuel_maximum_k']:.8g}",
                    "fuel_average_k": f"{row['fuel_average_k']:.8g}",
                    "fuel_surface_k": f"{row['fuel_average_k']:.8g}",
                    "clad_inner_k": f"{clad_max:.8g}",
                    "clad_outer_k": f"{clad_max:.8g}",
                    "water_temperature_k": f"{row['fluid_maximum_k']:.8g}",
                    "pressure_pa": f"{pressure_pa:.8g}",
                    "genfoam_total_power_w": f"{row.get('genfoam_total_power_w', 0.0):.8g}",
                }
            )


def _append_if_complete(
    rows: list[dict[str, float]],
    current: dict[str, float] | None,
) -> None:
    if current is None:
        return
    required = (
        "fuel_average_k",
        "fuel_maximum_k",
        "clad_maximum_k",
        "fluid_maximum_k",
    )
    if all(key in current for key in required):
        rows.append(dict(current))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pressure-pa", type=float, default=15.5e6)
    args = parser.parse_args()
    rows = parse_log(args.log)
    write_timeseries(rows, args.output, args.pressure_pa)
    print(f"Wrote {len(rows)} GeN-Foam rows to {args.output}")


if __name__ == "__main__":
    main()
