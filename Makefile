SHELL := /bin/zsh

TEX := main.tex
BUILD_DIR := build/latex
PDF := $(BUILD_DIR)/main.pdf

TEXBIN := /Library/TeX/texbin
PATH_WITH_TEX := $(TEXBIN):$(PATH)
ifneq ("$(wildcard .venv/bin/python)","")
PYTHON ?= .venv/bin/python
else
PYTHON ?= python3
endif

.PHONY: help check test pipeline-figures pdf pdf-latexmk pdf-xelatex pdf-tectonic clean pull-overleaf push-overleaf push-github

help:
	@echo "Targets:"
	@echo "  make check          Check local tools and git remotes"
	@echo "  make test           Compile Python modules and run smoke tests"
	@echo "  make pipeline-figures  Regenerate notebook-synced figures and tex fragment"
	@echo "  make pdf            Build build/latex/main.pdf"
	@echo "  make pdf-latexmk    Build with latexmk/xelatex"
	@echo "  make pdf-xelatex    Build with xelatex directly"
	@echo "  make pdf-tectonic   Build with tectonic"
	@echo "  make pull-overleaf  Pull master from Overleaf"
	@echo "  make push-overleaf  Push master to Overleaf"
	@echo "  make push-github    Push master to GitHub origin"
	@echo "  make clean          Remove build artifacts"

check:
	@echo "Repository:"
	@git status --short
	@echo
	@echo "Remotes:"
	@git remote -v
	@echo
	@echo "LaTeX tools:"
	@PATH="$(PATH_WITH_TEX)" sh -c 'command -v latexmk || true; command -v xelatex || true; command -v tectonic || true'

test:
	PYTHONPATH=src $(PYTHON) -m compileall -q src scripts
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests

pipeline-figures:
	@$(PYTHON) scripts/make_fig_fuel_pin_anatomy.py
	@$(PYTHON) scripts/make_fig_thermal_radial_relaxation.py
	@$(PYTHON) scripts/make_fig_poc_setup.py
	@$(PYTHON) scripts/make_fig_poc_gantt.py
	@$(PYTHON) scripts/export_pipeline_figures.py

pdf: pipeline-figures
	@PATH="$(PATH_WITH_TEX)" sh -c 'if command -v latexmk >/dev/null 2>&1 && command -v xelatex >/dev/null 2>&1; then $(MAKE) pdf-latexmk; elif command -v xelatex >/dev/null 2>&1; then $(MAKE) pdf-xelatex; else $(MAKE) pdf-tectonic; fi'

pdf-latexmk:
	@mkdir -p "$(BUILD_DIR)"
	@PATH="$(PATH_WITH_TEX)" latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir="$(BUILD_DIR)" "$(TEX)"
	@echo "Wrote $(PDF)"

pdf-xelatex:
	@mkdir -p "$(BUILD_DIR)"
	@PATH="$(PATH_WITH_TEX)" xelatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory="$(BUILD_DIR)" "$(TEX)"
	@PATH="$(PATH_WITH_TEX)" xelatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory="$(BUILD_DIR)" "$(TEX)"
	@echo "Wrote $(PDF)"

pdf-tectonic:
	@mkdir -p "$(BUILD_DIR)"
	@tectonic -X compile "$(TEX)" --outdir "$(BUILD_DIR)"
	@echo "Wrote $(PDF)"

pull-overleaf:
	git pull --ff-only overleaf master

push-overleaf:
	git push overleaf master

push-github:
	git push origin master

clean:
	rm -rf build
