# Diploma Modeling Notebooks

This repository is a compact public snapshot for the diploma modeling notebooks.
It keeps only the files needed to open and reproduce the notebook calculations:

- `notebooks/` -- executed notebooks with saved outputs for GitHub preview;
- `src/thesis_modeling/` -- reusable functions used by the notebooks;
- `data/genfoam/` -- compact GeN-Foam thermal time series used as notebook input;
- `pyproject.toml` -- Python dependencies and package metadata.

## Reproduce

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[chemistry,notebooks]'
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
```

Cantera is required for the equilibrium `H2` estimates. Generated figures, LaTeX
drafts, agent state, local environments, and other process artifacts are ignored.
