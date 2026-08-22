# `data/process` — processed / generated artifacts

This folder holds **outputs** derived from raw inputs or pipelines: aggregates, cleaned tables, and analysis exports.

Keep a clear line: `data/raw/` = original inputs; `data/process/` = things we generate.

## Purpose

- Separate source datasets from regenerated artifacts.
- Give exporters and pipelines a stable place to write results.
- Avoid committing noisy generated files when they can be reproduced locally.

## Current artifacts

| File | Produced by | What it is |
| --- | --- | --- |
| `results.csv` | `scripts/analyze.py` → `services.incidents_analysis.exporter` | Metric summary (`metric`, `value`, `percentage`). No `patient_id`. Regenerated when the user answers `y` to the export prompt. |

## Tips

- Prefer regenerating `results.csv` over hand-editing it.
- Do not store PHI/PII exports here.
- Generated CSVs like `results.csv` are listed in `.gitignore` when they are reproducible from `data/raw/`.

> Spanish version: [README.es.md](./README.es.md).
