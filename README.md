# Расчетные ноутбуки диплома

Репозиторий содержит публичный срез расчетной части диплома. В нем оставлены
только файлы, которые нужны для просмотра расчетов на GitHub и локального
воспроизведения:

- `notebooks/` -- выполненные ноутбуки с сохраненными выводами;
- `src/thesis_modeling/` -- функции, которые вызываются из ноутбуков;
- `data/genfoam/` -- компактные тепловые ряды GeN-Foam;
- `pyproject.toml` -- зависимости Python и метаданные пакета.

## Воспроизведение

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[chemistry,notebooks]'
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
```

Для равновесных оценок `H2` требуется Cantera. Черновики текста, LaTeX-сборка,
состояние агентов, локальные окружения и презентационные артефакты исключены
через `.gitignore`.
