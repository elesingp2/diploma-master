# Карта визуализаций диплома

Активные рисунки в `main.tex` сейчас сведены к теме ТВЭЛ--вода/пар: расчетная геометрия, радиальная тепловая релаксация и синхронизированный pipeline из ноутбука `notebooks/01_tvel_water_pipeline.ipynb`. Графики pipeline выводятся отдельными файлами: одна картинка отвечает на один расчетный вопрос. Старые доплеровские, memory-kernel и GeN-Foam diagnostic-графики больше не подключаются в диплом.

## Быстрая регенерация

Перед сборкой PDF:

```bash
make pipeline-figures
```

Команда запускает:

```bash
python3 scripts/export_pipeline_figures.py
```

Скрипт пересчитывает notebook-сценарии через `src/thesis_modeling/pipeline_export.py`, обновляет PNG и заново пишет `figures/pipeline_report.tex`. Цель `make pdf` вызывает `make pipeline-figures` автоматически.

## Активные рисунки и таблицы

| Объект | Файл | Подключение | Источник |
|---|---|---|---|
| `fig:fuelPinAnatomyTheory` | `figures/fig7_fuel_pin_anatomy.pdf` | `main.tex` | статичная схема расчетной области |
| `fig:thermalRadialRelaxation` | `figures/fig14_thermal_radial_relaxation.pdf` | `main.tex` | `scripts/make_fig_thermal_radial_relaxation.py` |
| `fig:pipelineGeometry` | `figures/pipeline_geometry.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `fig:pipelineTemperatureHistory` | `figures/pipeline_temperature_history.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `fig:pipelineRadialTemperatureMap` | `figures/pipeline_radial_temperature_map.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `fig:pipelineRadialTemperatureProfiles` | `figures/pipeline_radial_temperature_profiles.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `fig:pipelineEnergyBalance` | `figures/pipeline_energy_balance.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `fig:pipelineSteamState` | `figures/pipeline_steam_state.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `fig:pipelineChemistryWindow` | `figures/pipeline_chemistry_window.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `fig:pipelineCandidateWindow` | `figures/pipeline_candidate_window.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `tab:pipelineScenarioReport` | `figures/pipeline_report.tex` | `main.tex` через `\input` | `scripts/export_pipeline_figures.py` |

## Старые рабочие материалы

В `figures/` могут оставаться старые файлы `fig0_*`, `fig4_*`, `fig10_kernel_fit.png`, `fig15_*` и диагностические таблицы. Они не подключаются в активной сборке диплома и сохранены только как рабочий архив прежней постановки.
