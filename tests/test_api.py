"""API endpoint tests using httpx TestClient."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from labvault.web.app import create_app


@pytest.fixture
def client(tmp_path: Path):
    app = create_app(vault_path=tmp_path / "testvault")
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# --- Projects ---

def test_list_projects_empty(client):
    r = client.get("/api/projects")
    assert r.status_code == 200
    assert r.json() == []


def test_create_project(client):
    r = client.post("/api/projects", json={"name": "My Project", "description": "A test"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "My Project"
    assert data["slug"] == "my-project"


def test_get_project(client):
    client.post("/api/projects", json={"name": "CV"})
    r = client.get("/api/projects/cv")
    assert r.status_code == 200
    assert r.json()["name"] == "CV"


def test_get_project_not_found(client):
    r = client.get("/api/projects/nonexistent")
    assert r.status_code == 404


def test_delete_project(client):
    client.post("/api/projects", json={"name": "ToDelete"})
    r = client.delete("/api/projects/todelete")
    assert r.status_code == 204
    r = client.get("/api/projects/todelete")
    assert r.status_code == 404


# --- Experiments ---

def test_create_and_list_experiments(client):
    client.post("/api/projects", json={"name": "P"})
    r = client.post("/api/projects/p/experiments", json={"name": "LR Sweep"})
    assert r.status_code == 201
    assert r.json()["slug"] == "lr-sweep"

    r = client.get("/api/projects/p/experiments")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_experiment(client):
    client.post("/api/projects", json={"name": "P"})
    client.post("/api/projects/p/experiments", json={"name": "Exp"})
    r = client.get("/api/projects/p/experiments/exp")
    assert r.status_code == 200
    assert r.json()["name"] == "Exp"


# --- Runs ---

def _setup_project_and_experiment(client):
    client.post("/api/projects", json={"name": "Proj"})
    r = client.post("/api/projects/proj/experiments", json={"name": "Exp"})
    return r.json()["id"]


def test_create_run(client):
    exp_id = _setup_project_and_experiment(client)
    r = client.post(f"/api/experiments/{exp_id}/runs", json={
        "notes": "first run",
        "metrics": {"accuracy": 0.95},
        "tags": {"env": "local"},
    })
    assert r.status_code == 201
    data = r.json()
    assert data["version"] == 1
    assert data["metrics"]["accuracy"] == 0.95
    assert data["tags"]["env"] == "local"


def test_list_runs(client):
    exp_id = _setup_project_and_experiment(client)
    client.post(f"/api/experiments/{exp_id}/runs", json={"notes": "r1"})
    client.post(f"/api/experiments/{exp_id}/runs", json={"notes": "r2"})
    r = client.get(f"/api/experiments/{exp_id}/runs")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_run(client):
    exp_id = _setup_project_and_experiment(client)
    create_r = client.post(f"/api/experiments/{exp_id}/runs", json={"notes": "test"})
    run_id = create_r.json()["id"]
    r = client.get(f"/api/runs/{run_id}")
    assert r.status_code == 200
    assert r.json()["version"] == 1


def test_update_run(client):
    exp_id = _setup_project_and_experiment(client)
    create_r = client.post(f"/api/experiments/{exp_id}/runs", json={})
    run_id = create_r.json()["id"]
    r = client.patch(f"/api/runs/{run_id}", json={
        "metrics": {"f1": 0.88},
        "tags": {"gpu": "A100"},
        "notes": "updated notes",
    })
    assert r.status_code == 200
    assert r.json()["metrics"]["f1"] == 0.88
    assert r.json()["tags"]["gpu"] == "A100"
    assert r.json()["notes"] == "updated notes"


def test_seal_run(client):
    exp_id = _setup_project_and_experiment(client)
    create_r = client.post(f"/api/experiments/{exp_id}/runs", json={})
    run_id = create_r.json()["id"]
    r = client.post(f"/api/runs/{run_id}/seal")
    assert r.status_code == 200
    assert r.json()["status"] == "sealed"

    # Cannot seal again
    r = client.post(f"/api/runs/{run_id}/seal")
    assert r.status_code == 400


def test_sealed_run_rejects_update(client):
    exp_id = _setup_project_and_experiment(client)
    create_r = client.post(f"/api/experiments/{exp_id}/runs", json={})
    run_id = create_r.json()["id"]
    client.post(f"/api/runs/{run_id}/seal")
    r = client.patch(f"/api/runs/{run_id}", json={"notes": "should fail"})
    assert r.status_code == 400


# --- Search ---

def test_search(client):
    exp_id = _setup_project_and_experiment(client)
    client.post(f"/api/experiments/{exp_id}/runs", json={
        "notes": "baseline run",
        "tags": {"env": "local"},
        "metrics": {"accuracy": 0.92},
    })
    r = client.get("/api/search", params={"q": "baseline"})
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_search_by_tag(client):
    exp_id = _setup_project_and_experiment(client)
    client.post(f"/api/experiments/{exp_id}/runs", json={"tags": {"env": "local"}})
    client.post(f"/api/experiments/{exp_id}/runs", json={"tags": {"env": "cloud"}})
    r = client.get("/api/search", params={"tag": "env=local"})
    assert r.status_code == 200
    assert len(r.json()) == 1


# --- Compare ---

def test_compare(client):
    exp_id = _setup_project_and_experiment(client)
    r1 = client.post(f"/api/experiments/{exp_id}/runs", json={
        "metrics": {"f1": 0.85}, "tags": {"env": "local"},
    })
    r2 = client.post(f"/api/experiments/{exp_id}/runs", json={
        "metrics": {"f1": 0.92}, "tags": {"env": "cloud"},
    })
    r = client.post("/api/compare", json={
        "run_ids": [r1.json()["id"], r2.json()["id"]],
    })
    assert r.status_code == 200
    data = r.json()
    assert len(data["metric_deltas"]) == 1
    assert data["metric_deltas"][0]["key"] == "f1"


# --- Export ---

def test_export_csv(client):
    exp_id = _setup_project_and_experiment(client)
    client.post(f"/api/experiments/{exp_id}/runs", json={"metrics": {"acc": 0.9}})
    r = client.get("/api/export/table", params={"experiment_id": exp_id, "format": "csv"})
    assert r.status_code == 200
    assert "acc" in r.text


def test_export_latex(client):
    exp_id = _setup_project_and_experiment(client)
    client.post(f"/api/experiments/{exp_id}/runs", json={"metrics": {"acc": 0.9}})
    r = client.get("/api/export/table", params={"experiment_id": exp_id, "format": "latex"})
    assert r.status_code == 200
    assert "\\begin{table}" in r.text


def test_export_run_zip(client):
    exp_id = _setup_project_and_experiment(client)
    create_r = client.post(f"/api/experiments/{exp_id}/runs", json={})
    run_id = create_r.json()["id"]
    r = client.get(f"/api/export/run/{run_id}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"


# --- Stats & Frontend Static Files ---

def test_stats(client):
    exp_id = _setup_project_and_experiment(client)
    client.post(f"/api/experiments/{exp_id}/runs", json={})
    r = client.get("/api/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_projects"] == 1
    assert data["total_experiments"] == 1
    assert data["total_runs"] == 1
    assert "disk_usage_bytes" in data


def test_static_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "LabVault" in r.text
    assert "app-content" in r.text


def test_static_assets(client):
    r_css = client.get("/css/style.css")
    assert r_css.status_code == 200
    assert "--bg-base" in r_css.text

    r_js = client.get("/js/app.js")
    assert r_js.status_code == 200

    r_svg = client.get("/assets/logo.svg")
    assert r_svg.status_code == 200
    assert "<svg" in r_svg.text

