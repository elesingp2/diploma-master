# Карта визуализаций диплома

Активные рисунки в `main.tex` сейчас сведены к теме ТВЭЛ--вода/пар: анатомия расчетной области, радиальная тепловая задержка, V1-пайплайн для \(UO_2\)--Zircaloy и V2-пайплайн материаловедческого отбора. Графики pipeline выводятся отдельными файлами: одна картинка отвечает на один расчетный вопрос. Старые доплеровские, memory-kernel и GeN-Foam diagnostic-графики больше не подключаются в диплом.

## Быстрая регенерация

Перед сборкой PDF:

```bash
make pipeline-figures
```

Команда запускает:

```bash
python3 scripts/export_pipeline_figures.py
```

Цель `make pipeline-figures` обновляет все активные рисунки: `fig7_fuel_pin_anatomy`, `fig14_thermal_radial_relaxation`, V1-отчет и V2-отчет. Цель `make pdf` вызывает `make pipeline-figures` автоматически.

## Активные рисунки и таблицы

| Объект | Файл | Подключение | Источник |
|---|---|---|---|
| `fig:fuelPinAnatomyTheory` | `figures/fig7_fuel_pin_anatomy.pdf` | `main.tex` | `scripts/make_fig_fuel_pin_anatomy.py` |
| `fig:thermalRadialRelaxation` | `figures/fig14_thermal_radial_relaxation.pdf` | `main.tex` | `scripts/make_fig_thermal_radial_relaxation.py` |
| `fig:pipelineTemperatureHistory` | `figures/pipeline_temperature_history.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `fig:pipelineEnergyBalance` | `figures/pipeline_energy_balance.png` | `figures/pipeline_report.tex` | `scripts/export_pipeline_figures.py` |
| `fig:pipelineV2MaterialWindow` | `figures/pipeline_v2_material_window.png` | `figures/pipeline_v2_report.tex` | `src/thesis_modeling/pipeline_v2_export.py` |
| `tab:pipelineScenarioReport` | `figures/pipeline_report.tex` | `main.tex` через `\input` | `scripts/export_pipeline_figures.py` |
| `tab:pipelineV2MaterialScenarios` | `figures/pipeline_v2_report.tex` | `main.tex` через `\input` | `src/thesis_modeling/pipeline_v2_export.py` |

## Старые рабочие материалы

В `figures/` могут оставаться старые файлы `fig0_*`, `fig4_*`, `fig10_kernel_fit.png`, `fig15_*` и диагностические таблицы. Они не подключаются в активной сборке диплома и сохранены только как рабочий архив прежней постановки.
