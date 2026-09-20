# Quickstart Guide

Get from zero to managing experiments in under 5 minutes.

## 1. Install LabVault

```bash
pip install labvault
```

Verify:

```bash
labvault --help
```

## 2. Initialize a Vault

A vault is a directory where LabVault stores your experiments, runs, and artifacts.

```bash
mkdir my-research && cd my-research
labvault init .
```

This creates a `labvault.db` SQLite database and a `projects/` directory.

## 3. Create Your First Project & Experiment

```bash
labvault project create "Image Classification"
labvault experiment create image-classification "ResNet vs ViT"
```

## 4. Log Your First Run

After training a model, log the results:

```bash
labvault run start image-classification resnet-vs-vit \
  --metric accuracy=0.92 \
  --metric val_loss=0.34 \
  --tag model=resnet50 \
  --tag optimizer=adam \
  --tag lr=0.001 \
  --notes "Baseline ResNet-50 with default settings"
```

## 5. Add Artifacts

Attach your model weights, training scripts, and results:

```bash
labvault artifact add image-classification resnet-vs-vit 1 ./model.pt
labvault artifact add image-classification resnet-vs-vit 1 ./train.py
labvault artifact add image-classification resnet-vs-vit 1 ./results.json --auto-metrics
```

The `--auto-metrics` flag automatically extracts numeric values from `.json` and `.csv` files and logs them as metrics.

## 6. Run a Second Experiment

```bash
labvault run start image-classification resnet-vs-vit \
  --metric accuracy=0.95 \
  --metric val_loss=0.21 \
  --tag model=vit-base \
  --tag optimizer=adamw \
  --tag lr=0.0003
```

## 7. Compare Runs

See what changed between your two runs:

```bash
labvault diff image-classification resnet-vs-vit 1 2
```

This renders a beautiful terminal table with color-coded deltas.

## 8. Export for a Paper

Generate a LaTeX table for your paper:

```bash
labvault export-table image-classification resnet-vs-vit --format latex
```

Or export as CSV/Markdown/JSON:

```bash
labvault export-table image-classification resnet-vs-vit --format csv -o results.csv
```

## 9. Launch the Web Dashboard

```bash
labvault ui
```

Opens a browser at `http://localhost:5555` with:
- Project and experiment overview
- Sortable results tables
- Inline artifact previews (images, code, CSV data grids)
- Side-by-side run comparison with code diffs and image sliders
- Global search across all runs

## 10. Check Vault Health

```bash
labvault doctor
```

Verifies that all database records have corresponding files on disk and vice versa.

---

## What's Next?

- **Search**: `labvault search --tag model=resnet --metric "accuracy > 0.9"`
- **Seal runs**: `labvault run seal image-classification resnet-vs-vit 1` (make immutable)
- **Watch a directory**: `labvault watch ./outputs image-classification resnet-vs-vit` (auto-ingest)
- **Pack for sharing**: `labvault pack image-classification resnet-vs-vit 1 -o run.zip`
