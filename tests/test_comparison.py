"""Tests for core/comparison.py — compare_runs and compare_file_contents."""

from pathlib import Path

from labvault.core.vault import Vault
from labvault.core.project import create_project
from labvault.core.experiment import create_experiment
from labvault.core.run import create_run
from labvault.core.metrics import add_metrics
from labvault.core.tags import add_tags
from labvault.core.artifact import add_artifact
from labvault.core.comparison import compare_runs, compare_file_contents


def _make_vault_with_two_runs(tmp_path: Path):
    """Helper: create a vault with 2 runs in the same experiment."""
    vault = Vault.init(tmp_path)
    project = create_project(vault, "Comp Project")
    experiment = create_experiment(vault, project, "Ablation A")

    run1 = create_run(vault, experiment, tags={"lr": "0.001"}, metrics={"accuracy": 0.92, "loss": 0.3})
    run2 = create_run(vault, experiment, tags={"lr": "0.01"}, metrics={"accuracy": 0.95, "loss": 0.2})
    return vault, project, experiment, run1, run2


# ────────── compare_runs tests ──────────

def test_compare_runs_basic(tmp_path: Path):
    vault, _, _, run1, run2 = _make_vault_with_two_runs(tmp_path)
    result = compare_runs(vault, [run1.id, run2.id])

    assert set(result.run_ids) == {run1.id, run2.id}
    assert result.run_versions[run1.id] == 1
    assert result.run_versions[run2.id] == 2


def test_compare_runs_metric_deltas(tmp_path: Path):
    vault, _, _, run1, run2 = _make_vault_with_two_runs(tmp_path)
    result = compare_runs(vault, [run1.id, run2.id])

    # Find accuracy delta
    acc = next(m for m in result.metric_deltas if m.key == "accuracy")
    assert acc.values[run1.id] == 0.92
    assert acc.values[run2.id] == 0.95
    assert acc.spread == 0.95 - 0.92

    # Find loss delta
    loss = next(m for m in result.metric_deltas if m.key == "loss")
    assert loss.values[run1.id] == 0.3
    assert loss.values[run2.id] == 0.2


def test_compare_runs_tag_diffs(tmp_path: Path):
    vault, _, _, run1, run2 = _make_vault_with_two_runs(tmp_path)
    result = compare_runs(vault, [run1.id, run2.id])

    lr_tag = next(t for t in result.tag_diffs if t.key == "lr")
    assert lr_tag.values[run1.id] == "0.001"
    assert lr_tag.values[run2.id] == "0.01"
    assert lr_tag.is_uniform is False


def test_compare_runs_artifact_presence(tmp_path: Path):
    vault, _, experiment, run1, run2 = _make_vault_with_two_runs(tmp_path)

    # Add an artifact to run1 only
    code_file = tmp_path / "train.py"
    code_file.write_text("print('hello')", encoding="utf-8")
    add_artifact(vault, run1, code_file)

    result = compare_runs(vault, [run1.id, run2.id])
    art_diff = next(a for a in result.artifact_diffs if a.filename == "train.py")
    assert run1.id in art_diff.present_in
    assert run2.id not in art_diff.present_in


def test_compare_runs_three_runs(tmp_path: Path):
    vault, project, experiment, run1, run2 = _make_vault_with_two_runs(tmp_path)
    run3 = create_run(vault, experiment, metrics={"accuracy": 0.88})

    result = compare_runs(vault, [run1.id, run2.id, run3.id])
    assert len(result.run_ids) == 3

    acc = next(m for m in result.metric_deltas if m.key == "accuracy")
    assert acc.min_val == 0.88
    assert acc.max_val == 0.95


def test_compare_runs_requires_two(tmp_path: Path):
    vault = Vault.init(tmp_path)
    project = create_project(vault, "P")
    experiment = create_experiment(vault, project, "E")
    run1 = create_run(vault, experiment)

    try:
        compare_runs(vault, [run1.id])
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ────────── compare_file_contents tests ──────────

def test_compare_text_file(tmp_path: Path):
    vault, _, experiment, run1, run2 = _make_vault_with_two_runs(tmp_path)

    # Create two different versions of a text file
    file_v1 = tmp_path / "train_v1.py"
    file_v1.write_text("lr = 0.001\nepochs = 10\n", encoding="utf-8")
    add_artifact(vault, run1, file_v1, artifact_type="code")

    # Rename to same name for run2
    file_v2 = tmp_path / "train_v2.py"
    file_v2.write_text("lr = 0.01\nepochs = 20\n", encoding="utf-8")

    # We need to add with same filename — copy to a temp location with the same name
    same_name_file = tmp_path / "upload" / "train_v1.py"
    same_name_file.parent.mkdir(exist_ok=True)
    same_name_file.write_text("lr = 0.01\nepochs = 20\n", encoding="utf-8")
    add_artifact(vault, run2, same_name_file, artifact_type="code")

    result = compare_file_contents(vault, [run1.id, run2.id], "train_v1.py")
    assert result.diff_type == "text"
    assert len(result.diff_lines) > 0  # Should have diff output
    assert result.filename == "train_v1.py"


def test_compare_identical_text_file(tmp_path: Path):
    vault, _, experiment, run1, run2 = _make_vault_with_two_runs(tmp_path)

    # Create identical files in both runs
    file_a = tmp_path / "same.py"
    file_a.write_text("x = 1\n", encoding="utf-8")
    add_artifact(vault, run1, file_a)

    file_b = tmp_path / "upload" / "same.py"
    file_b.parent.mkdir(exist_ok=True)
    file_b.write_text("x = 1\n", encoding="utf-8")
    add_artifact(vault, run2, file_b)

    result = compare_file_contents(vault, [run1.id, run2.id], "same.py")
    assert result.diff_type == "text"
    assert len(result.diff_lines) == 0  # Identical files


def test_compare_image_file(tmp_path: Path):
    vault, _, experiment, run1, run2 = _make_vault_with_two_runs(tmp_path)

    # Create minimal PNG (1x1 pixel) for both runs
    import struct, zlib
    def make_png(r, g, b):
        raw = b'\x00' + bytes([r, g, b])
        return (b'\x89PNG\r\n\x1a\n' +
                b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde' +
                struct.pack('>I', len(zlib.compress(raw))) + b'IDAT' + zlib.compress(raw) +
                struct.pack('>I', zlib.crc32(b'IDAT' + zlib.compress(raw)) & 0xFFFFFFFF) +
                b'\x00\x00\x00\x00IEND\xaeB`\x82')

    png1 = tmp_path / "fig.png"
    png1.write_bytes(make_png(255, 0, 0))
    add_artifact(vault, run1, png1)

    png2_dir = tmp_path / "upload2"
    png2_dir.mkdir(exist_ok=True)
    png2 = png2_dir / "fig.png"
    png2.write_bytes(make_png(0, 255, 0))
    add_artifact(vault, run2, png2)

    result = compare_file_contents(vault, [run1.id, run2.id], "fig.png")
    assert result.diff_type == "image"
    assert len(result.images) == 2
    assert all(v.startswith("data:image/png;base64,") for v in result.images.values())


def test_compare_binary_file(tmp_path: Path):
    vault, _, experiment, run1, run2 = _make_vault_with_two_runs(tmp_path)

    # Create a .pkl file (unknown binary)
    bin1 = tmp_path / "model.pkl"
    bin1.write_bytes(b'\x80\x04\x95\x00\x00')
    add_artifact(vault, run1, bin1)

    bin2_dir = tmp_path / "upload3"
    bin2_dir.mkdir(exist_ok=True)
    bin2 = bin2_dir / "model.pkl"
    bin2.write_bytes(b'\x80\x04\x95\x01\x00')
    add_artifact(vault, run2, bin2)

    result = compare_file_contents(vault, [run1.id, run2.id], "model.pkl")
    assert result.diff_type == "binary"
    assert len(result.sizes) == 2


def test_compare_file_missing_in_one_run(tmp_path: Path):
    vault, _, experiment, run1, run2 = _make_vault_with_two_runs(tmp_path)

    # Only add to run1
    f = tmp_path / "only_v1.py"
    f.write_text("x = 1", encoding="utf-8")
    add_artifact(vault, run1, f)

    result = compare_file_contents(vault, [run1.id, run2.id], "only_v1.py")
    # Should fall back to binary since only 1 copy exists
    assert result.diff_type == "binary"
