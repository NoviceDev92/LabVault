# LabVault

**A local-first, zero-cost experiment management platform for ML researchers.**

> Stop paying for cloud experiment trackers. Stop losing track of which hyperparameters produced your best model. LabVault gives you the power of Weights & Biases — entirely on your local machine, with zero accounts, zero internet, and zero cost.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🗄️ **Project Organization** | Hierarchical structure: Projects → Experiments → Runs (auto-versioned) |
| 📊 **Metric & Tag Tracking** | Log arbitrary key-value metrics and tags per run |
| 📦 **Artifact Management** | Attach model weights, scripts, configs, figures — any file — to a run |
| 🔍 **Full-Text Search** | FTS5-powered search across notes, tags, and metrics |
| ⚡ **Ablation Comparison** | Side-by-side run diffs with color-coded metric deltas |
| 📄 **Code Diff Viewer** | Unified diff for shared text files between runs |
| 🖼️ **Image Comparison** | Pixel-level slider for comparing generated figures across runs |
| 📤 **Publication Export** | One-command LaTeX, CSV, Markdown, and JSON table export |
| 🌐 **Web Dashboard** | Beautiful dark-themed SPA served locally — no Node.js required |
| 🩺 **Vault Doctor** | Integrity checker to verify DB ↔ filesystem consistency |
| 👁️ **Directory Watcher** | `labvault watch` auto-ingests files as new runs appear |
| 🔒 **Run Sealing** | Mark runs as immutable to prevent accidental modification |
| 🗑️ **Soft Delete & Recovery** | Trash and restore runs without data loss |

---

## 🚀 Quickstart

### Install

```bash
pip install labvault
```

Or install from source:

```bash
git clone https://github.com/NoviceDev92/LabVault.git
cd LabVault
pip install -e .
```

### Initialize a Vault

```bash
labvault init ./my-research
cd my-research
```

### Run Your First Experiment

```bash
# Create a project and experiment
labvault project create "Sentiment Analysis"
labvault experiment create sentiment-analysis "LR Sweep"

# Start a run with metrics and tags
labvault run start sentiment-analysis lr-sweep \
  --metric accuracy=0.92 --metric loss=0.35 \
  --tag lr=0.001 --tag model=bert-base \
  --notes "Baseline run with default hyperparameters"

# Add artifact files
labvault artifact add sentiment-analysis lr-sweep 1 ./model.pt
labvault artifact add sentiment-analysis lr-sweep 1 ./results.json --auto-metrics

# Start a second run
labvault run start sentiment-analysis lr-sweep \
  --metric accuracy=0.95 --metric loss=0.22 \
  --tag lr=0.01 --tag model=bert-base

# Compare the two runs
labvault diff sentiment-analysis lr-sweep 1 2
```

### Launch the Web Dashboard

```bash
labvault ui
# Opens at http://localhost:5555
```

---

## 🖥️ CLI Reference

### Core Commands

| Command | Description |
|---|---|
| `labvault init [path]` | Initialize a new vault |
| `labvault ui [--port N]` | Launch the web dashboard |
| `labvault stats` | Show vault-wide summary statistics |
| `labvault config --show` | View current configuration |
| `labvault doctor` | Check vault integrity |

### Project & Experiment Management

| Command | Description |
|---|---|
| `labvault project create <name>` | Create a new project |
| `labvault project list` | List all projects |
| `labvault experiment create <proj> <name>` | Create a new experiment |
| `labvault experiment list <proj>` | List experiments in a project |

### Run Lifecycle

| Command | Description |
|---|---|
| `labvault run start <proj> <exp> [--metric K=V] [--tag K=V] [--notes "..."]` | Start a new run |
| `labvault run log <proj> <exp> <version> --metric K=V --tag K=V` | Log metrics/tags to an existing run |
| `labvault run seal <proj> <exp> <version>` | Mark a run as immutable |
| `labvault show <proj> <exp> <version>` | Show detailed run info |

### Artifacts

| Command | Description |
|---|---|
| `labvault artifact add <proj> <exp> <version> <file> [--auto-metrics]` | Attach a file to a run |

### Search & Compare

| Command | Description |
|---|---|
| `labvault search --tag K=V --metric "f1 > 0.9" --query "text"` | Search across all runs |
| `labvault diff <proj> <exp> <v1> <v2>` | Compare two runs side-by-side |

### Export & Share

| Command | Description |
|---|---|
| `labvault export-table <proj> <exp> --format latex\|csv\|markdown\|json` | Export results table |
| `labvault pack <proj> <exp> <version> [--output path.zip]` | Pack a run as a ZIP |

### Utilities

| Command | Description |
|---|---|
| `labvault watch <dir> <proj> <exp>` | Auto-ingest files from a directory |
| `labvault trash list` | List soft-deleted runs |
| `labvault trash restore <run_id>` | Restore a trashed run |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────┐
│                   CLI (Click)                │
│      labvault add / log / diff / export      │
├──────────────────────────────────────────────┤
│                Web UI (FastAPI)               │
│        REST API + Vanilla JS SPA             │
├──────────────────────────────────────────────┤
│              Core Business Logic              │
│   vault / project / experiment / run / ...   │
├──────────────────────────────────────────────┤
│              Storage Engine                   │
│          SQLite + Local Filesystem            │
└──────────────────────────────────────────────┘
```

**Key design decisions:**
- **Core has zero framework dependencies** — the business logic is pure Python. CLI and Web are thin wrappers.
- **SQLite is the database AND the search engine** (via FTS5). No external services.
- **Frontend is zero-build** — vanilla HTML/CSS/JS served by FastAPI. No Node.js, no npm, no webpack.

---

## ⚙️ Configuration

LabVault stores its config at `~/.labvault/config.yaml`:

```yaml
ui:
  port: 5555
  theme: dark
default_project: null
auto_metrics: false
```

Modify via CLI:

```bash
labvault config --set ui.port=8080
labvault config --set default_project=my-project
labvault config --show
```

---

## 📁 Vault Structure

```
my-research/
├── labvault.db              # SQLite database (metadata, metrics, tags, FTS index)
├── projects/
│   └── sentiment-analysis/
│       └── lr-sweep/
│           ├── v1/
│           │   ├── _meta.json
│           │   ├── model.pt
│           │   └── results.json
│           └── v2/
│               ├── _meta.json
│               └── config.yaml
└── .trash/                  # Soft-deleted items
```

Every run directory contains a `_meta.json` file, making the vault **browsable even without LabVault installed**.

---

## 🧪 Development

```bash
# Clone and install in dev mode
git clone https://github.com/NoviceDev92/LabVault.git
cd LabVault
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/
```

---

## 📝 Philosophy

LabVault is built on three principles:

1. **Local-first.** Your data lives on your machine. No cloud accounts, no internet required, no vendor lock-in.
2. **Zero-cost.** Free forever. No premium tiers, no seat licenses, no usage limits.
3. **Researcher-friendly.** If you can `pip install`, you can use LabVault. No Docker, no Node.js, no infrastructure.

---

## 📄 License

MIT — use it however you want.
