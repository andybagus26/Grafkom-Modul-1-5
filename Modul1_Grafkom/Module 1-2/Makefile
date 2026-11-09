# Module 1 -- Digital Representation, Colour & Memory
# POSIX make. On Windows use Git Bash / WSL, or run the `python ...` lines by hand.
# PY: use `python3` when it exists (macOS / most Linux ship no `python`), else `python`.
PY ?= $(shell command -v python3 >/dev/null 2>&1 && echo python3 || echo python)

.PHONY: all data test report figures clean

all: data test report

## generate the deterministic synthetic heritage image set -> data/
data:
	$(PY) make_data.py --out data

## run every from-scratch unit's self-test + its reference match
test: data
	$(PY) tests.py

## build report/budget.md + formats.md + report.html + every artifact they show
report: data
	$(PY) lab1.py
	$(PY) gamma_resize_bug.py --fix --out report/
	$(PY) resample.py --image data/relief.ppm --factor 2 --methods naive-box,linear-box --out report/
	$(PY) format_compare.py --image data/crop_hifreq.ppm --out report/
	$(PY) format_compare.py --image data/crop_smooth.ppm --out report/
	$(PY) baseline_compare.py --out report/
	$(PY) banding.py --out report/
	$(PY) aliasing.py --out report/
	$(PY) report.py
	@echo "open report/report.html"

## figures for the pre-study / report (hand-written SVG, no plotting library)
figures:
	$(PY) figures_m1.py

clean:
	rm -rf data report _tmp_selftest.* __pycache__
