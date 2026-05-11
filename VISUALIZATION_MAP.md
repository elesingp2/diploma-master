# Карта визуализаций диплома

Активные рисунки в `main.tex` сейчас сведены к теме ТВЭЛ--вода/пар: расчетная геометрия, радиальная тепловая релаксация и синхронизированный pipeline из ноутбука `notebooks/01_tvel_water_pipeline.ipynb`. Старые доплеровские, memory-kernel и GeN-Foam diagnostic-графики больше не подключаются в диплом.

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
| `fig:pipelineTvelOverview` | `figures/pipeline_tvel_overview.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `fig:pipelineWaterEnergy` | `figures/pipeline_water_energy.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `fig:pipelineChemistryWindow` | `figures/pipeline_chemistry_window.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `tab:pipelineScenarioReport` | `figures/pipeline_report.tex` | `main.tex` через `\input` | `scripts/export_pipeline_figures.py` |

## Старые рабочие материалы

В `figures/` могут оставаться старые файлы `fig0_*`, `fig4_*`, `fig10_kernel_fit.png`, `fig15_*` и диагностические таблицы. Они не подключаются в активной сборке диплома и сохранены только как рабочий архив прежней постановки.
