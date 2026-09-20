# CLI Reference

Complete reference for all LabVault commands.

---

## Global Options

All commands support `--vault <path>` to specify the vault root (defaults to current directory).

---

## `labvault init [PATH]`

Initialize a new vault.

```bash
labvault init .
labvault init ~/my-research
```

**Arguments:**
- `PATH` — Directory to initialize (default: current directory)

---

## `labvault project`

### `labvault project create <NAME> [--description TEXT]`

Create a new project.

```bash
labvault project create "Sentiment Analysis" --description "NLP classification experiments"
```

### `labvault project list`

List all projects.

```bash
labvault project list
```

### `labvault project delete <SLUG>`

Soft-delete a project (moved to trash).

---

## `labvault experiment`

### `labvault experiment create <PROJECT_SLUG> <NAME> [--description TEXT]`

Create an experiment within a project.

```bash
labvault experiment create sentiment-analysis "LR Sweep"
```

### `labvault experiment list <PROJECT_SLUG>`

List experiments in a project.

---

## `labvault run`

### `labvault run start <PROJECT> <EXPERIMENT> [OPTIONS]`

Start a new run.

**Options:**
- `--metric, -m KEY=VALUE` — Log a metric (repeatable)
- `--tag, -t KEY=VALUE` — Log a tag (repeatable)
- `--notes TEXT` — Free-text notes

```bash
labvault run start my-proj lr-sweep \
  -m accuracy=0.92 -m loss=0.35 \
  -t lr=0.001 -t model=bert \
  --notes "Baseline run"
```

### `labvault run log <PROJECT> <EXPERIMENT> <VERSION> [OPTIONS]`

Add metrics or tags to an existing run.

```bash
labvault run log my-proj lr-sweep 1 -m f1=0.88 -t status=complete
```

### `labvault run seal <PROJECT> <EXPERIMENT> <VERSION>`

Seal a run to make it immutable.

```bash
labvault run seal my-proj lr-sweep 1
```

### `labvault run delete <PROJECT> <EXPERIMENT> <VERSION>`

Soft-delete a run.

---

## `labvault artifact`

### `labvault artifact add <PROJECT> <EXPERIMENT> <VERSION> <FILE> [OPTIONS]`

Add a file artifact to a run.

**Options:**
- `--type TYPE` — Override auto-detected artifact type
- `--auto-metrics` — Extract numeric metrics from `.json`/`.csv` files

```bash
labvault artifact add my-proj lr-sweep 1 ./model.pt
labvault artifact add my-proj lr-sweep 1 ./results.json --auto-metrics
```

---

## `labvault show <PROJECT> <EXPERIMENT> <VERSION>`

Display detailed information about a run: metadata, metrics, tags, and artifacts.

```bash
labvault show my-proj lr-sweep 1
```

---

## `labvault search`

Search across all runs in the vault.

**Options:**
- `--query, -q TEXT` — Full-text search in notes
- `--tag KEY=VALUE` — Filter by tag
- `--metric EXPR` — Filter by metric expression (e.g., `"f1 > 0.9"`)
- `--after DATE` — Filter runs created after date
- `--before DATE` — Filter runs created before date

```bash
labvault search --tag model=bert --metric "accuracy > 0.9"
labvault search --query "baseline" --after 2024-01-01
```

---

## `labvault diff <PROJECT> <EXPERIMENT> <V1> <V2>`

Compare two runs side-by-side with color-coded deltas.

```bash
labvault diff my-proj lr-sweep 1 2
```

Outputs:
- **Metric Deltas** — green/red percentage changes
- **Tag Differences** — highlighted discrepancies
- **Artifact Comparison** — file presence and sizes

---

## `labvault export-table <PROJECT> <EXPERIMENT>`

Export an experiment's results as a formatted table.

**Options:**
- `--format csv|latex|markdown|json` — Output format (default: csv)
- `--output, -o PATH` — Write to file instead of stdout

```bash
labvault export-table my-proj lr-sweep --format latex
labvault export-table my-proj lr-sweep --format csv -o results.csv
```

---

## `labvault pack <PROJECT> <EXPERIMENT> <VERSION>`

Pack a run and all its artifacts into a portable ZIP archive.

**Options:**
- `--output, -o PATH` — Output file path

```bash
labvault pack my-proj lr-sweep 1 -o run_v1.zip
```

---

## `labvault watch <DIRECTORY> <PROJECT> <EXPERIMENT>`

Monitor a directory and auto-create runs when new files appear.

**Options:**
- `--debounce N` — Seconds to wait for writes to settle (default: 3)

```bash
labvault watch ./outputs my-proj lr-sweep --debounce 5
```

Press `Ctrl+C` to stop.

---

## `labvault trash`

### `labvault trash list`

List all soft-deleted (trashed) items.

### `labvault trash restore <RUN_ID>`

Restore a trashed run.

---

## `labvault stats`

Show vault-wide summary: total projects, experiments, runs, artifacts, and disk usage.

```bash
labvault stats
```

---

## `labvault config`

View or modify global configuration.

**Options:**
- `--show` — Display all config values (default behavior)
- `--set KEY=VALUE` — Set a config value
- `--get KEY` — Get a specific config value

```bash
labvault config --show
labvault config --set ui.port=8080
labvault config --get ui.theme
```

---

## `labvault doctor`

Run a vault integrity check.

```bash
labvault doctor
```

Checks:
- Every artifact in the database has a corresponding file on disk
- Every file on disk has a corresponding database record
- Content hashes match the stored values
- Every run directory contains a `_meta.json` file

---

## `labvault ui [--port N]`

Launch the web dashboard.

```bash
labvault ui
labvault ui --port 8080
```

Opens a local web server at `http://localhost:PORT` with:
- Project/experiment overview
- Sortable results tables
- Inline artifact previews
- Run comparison with code diffs and image sliders
- Global search
- API docs at `/docs`
