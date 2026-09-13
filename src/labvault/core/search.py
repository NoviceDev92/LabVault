"""Search engine backed by SQLite FTS5."""

import re
from dataclasses import dataclass
from typing import Optional

from labvault.core.vault import Vault


@dataclass
class SearchResult:
    run_id: int
    project_name: str
    project_slug: str
    experiment_name: str
    experiment_slug: str
    version: int
    notes: Optional[str]
    metrics: dict[str, float]
    tags: dict[str, str]


def update_search_index(vault: Vault, run_id: int) -> None:
    """Populate or update the FTS5 search index for a specific run."""
    with vault.get_connection() as conn:
        # Fetch run info with project/experiment names
        row = conn.execute(
            """
            SELECT r.id, p.name, e.name, r.notes
            FROM runs r
            JOIN experiments e ON r.experiment_id = e.id
            JOIN projects p ON e.project_id = p.id
            WHERE r.id = ?
            """,
            (run_id,),
        ).fetchone()

        if not row:
            return

        rid, project_name, experiment_name, run_notes = row

        # Gather tags and metric keys
        tag_rows = conn.execute(
            "SELECT key, value FROM tags WHERE run_id = ?", (rid,)
        ).fetchall()
        tag_values = " ".join(f"{k} {v}" for k, v in tag_rows)

        metric_rows = conn.execute(
            "SELECT key FROM metrics WHERE run_id = ?", (rid,)
        ).fetchall()
        metric_keys = " ".join(k for (k,) in metric_rows)

        # Remove old entry if exists
        conn.execute("DELETE FROM search_index WHERE run_id = ?", (str(rid),))

        # Insert new entry
        conn.execute(
            "INSERT INTO search_index (run_id, project_name, experiment_name, run_notes, tag_values, metric_keys) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(rid), project_name or "", experiment_name or "", run_notes or "", tag_values, metric_keys),
        )


def _parse_metric_filter(expr: str) -> tuple[str, str, float]:
    """Parse 'f1 > 0.9' into ('f1', '>', 0.9)."""
    match = re.match(r"^\s*(\w+)\s*(>=|<=|>|<|=)\s*([\d.]+)\s*$", expr)
    if not match:
        raise ValueError(f"Invalid metric filter: '{expr}'. Use format: KEY OP VALUE (e.g., 'f1 > 0.9')")
    key, op, val = match.groups()
    return key, op, float(val)


def search(
    vault: Vault,
    query: Optional[str] = None,
    tag_filters: Optional[list[str]] = None,
    metric_filters: Optional[list[str]] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> list[SearchResult]:
    """
    Search runs using FTS5 text, tag filters, metric range filters, and date ranges.
    All filters are combined with AND logic.
    """
    with vault.get_connection() as conn:
        # Start by collecting matching run IDs from each filter, then intersect
        candidate_ids: Optional[set[int]] = None

        # 1. FTS5 text search
        if query:
            fts_rows = conn.execute(
                "SELECT run_id FROM search_index WHERE search_index MATCH ?",
                (query,),
            ).fetchall()
            fts_ids = {int(r[0]) for r in fts_rows}
            candidate_ids = fts_ids if candidate_ids is None else candidate_ids & fts_ids

        # 2. Tag filters (key=value)
        if tag_filters:
            for tf in tag_filters:
                if "=" not in tf:
                    raise ValueError(f"Invalid tag filter: '{tf}'. Use KEY=VALUE.")
                key, value = tf.split("=", 1)
                tag_rows = conn.execute(
                    "SELECT run_id FROM tags WHERE key = ? AND value = ?",
                    (key.strip(), value.strip()),
                ).fetchall()
                tag_ids = {r[0] for r in tag_rows}
                candidate_ids = tag_ids if candidate_ids is None else candidate_ids & tag_ids

        # 3. Metric range filters (e.g., "f1 > 0.9")
        if metric_filters:
            for mf in metric_filters:
                key, op, val = _parse_metric_filter(mf)
                # Map operator to SQL
                sql_op = op if op != "=" else "="
                metric_rows = conn.execute(
                    f"SELECT run_id FROM metrics WHERE key = ? AND value {sql_op} ?",
                    (key, val),
                ).fetchall()
                met_ids = {r[0] for r in metric_rows}
                candidate_ids = met_ids if candidate_ids is None else candidate_ids & met_ids

        # 4. Date range filters
        if after:
            date_rows = conn.execute(
                "SELECT id FROM runs WHERE created_at >= ?", (after,)
            ).fetchall()
            date_ids = {r[0] for r in date_rows}
            candidate_ids = date_ids if candidate_ids is None else candidate_ids & date_ids

        if before:
            date_rows = conn.execute(
                "SELECT id FROM runs WHERE created_at <= ?", (before,)
            ).fetchall()
            date_ids = {r[0] for r in date_rows}
            candidate_ids = date_ids if candidate_ids is None else candidate_ids & date_ids

        # If no filters provided, return all runs
        if candidate_ids is None:
            run_rows = conn.execute(
                """
                SELECT r.id, p.name, p.slug, e.name, e.slug, r.version, r.notes
                FROM runs r
                JOIN experiments e ON r.experiment_id = e.id
                JOIN projects p ON e.project_id = p.id
                ORDER BY r.created_at DESC
                """
            ).fetchall()
        elif not candidate_ids:
            return []
        else:
            placeholders = ",".join("?" * len(candidate_ids))
            run_rows = conn.execute(
                f"""
                SELECT r.id, p.name, p.slug, e.name, e.slug, r.version, r.notes
                FROM runs r
                JOIN experiments e ON r.experiment_id = e.id
                JOIN projects p ON e.project_id = p.id
                WHERE r.id IN ({placeholders})
                ORDER BY r.created_at DESC
                """,
                list(candidate_ids),
            ).fetchall()

        results = []
        for row in run_rows:
            rid, pname, pslug, ename, eslug, version, notes = row

            metrics_rows = conn.execute(
                "SELECT key, value FROM metrics WHERE run_id = ?", (rid,)
            ).fetchall()
            metrics = {k: v for k, v in metrics_rows}

            tags_rows = conn.execute(
                "SELECT key, value FROM tags WHERE run_id = ?", (rid,)
            ).fetchall()
            tags = {k: v for k, v in tags_rows}

            results.append(SearchResult(
                run_id=rid,
                project_name=pname,
                project_slug=pslug,
                experiment_name=ename,
                experiment_slug=eslug,
                version=version,
                notes=notes,
                metrics=metrics,
                tags=tags,
            ))

        return results
