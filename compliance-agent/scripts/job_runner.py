"""Generic resumable job runner.

Goal: Make long LLM workflows (eval, extraction, ruleset refactor) resumable by:
- planning stable work items
- checkpointing after each batch
- resuming by skipping completed item_ids

This module is intentionally small and dependency-free (uses existing YAML helpers).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional


# The repo already ships YAML helpers in many scripts; to avoid circular imports,
# we allow caller to pass load/dump callables.
LoadFn = Callable[[Path], dict]
DumpFn = Callable[[dict, Path], None]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class JobState:
    job_id: str
    pipeline_id: str
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    # Stable plan
    work_items: list[dict] = field(default_factory=list)

    # Execution cursor
    cursor: int = 0  # index of next item to process

    # Completed items keyed by item_id
    completed: dict[str, dict] = field(default_factory=dict)

    # Free-form notes / errors
    notes: list[str] = field(default_factory=list)

    def mark_completed(self, item_id: str, *, status: str = "ok", outputs: Optional[list[str]] = None) -> None:
        self.completed[item_id] = {
            "status": status,
            "outputs": outputs or [],
            "updated_at": utc_now_iso(),
        }

    def is_completed(self, item_id: str) -> bool:
        return item_id in self.completed and (self.completed[item_id] or {}).get("status") == "ok"


def load_state(path: Path, *, load_yaml: LoadFn) -> Optional[JobState]:
    if not path.exists():
        return None
    doc = load_yaml(path) or {}
    try:
        st = JobState(
            job_id=str(doc.get("job_id")),
            pipeline_id=str(doc.get("pipeline_id")),
        )
    except Exception:
        return None

    st.created_at = str(doc.get("created_at") or st.created_at)
    st.updated_at = str(doc.get("updated_at") or st.updated_at)
    st.work_items = list(doc.get("work_items") or [])
    st.cursor = int(doc.get("cursor") or 0)
    st.completed = dict(doc.get("completed") or {})
    st.notes = list(doc.get("notes") or [])
    return st


def save_state(state: JobState, path: Path, *, dump_yaml: DumpFn) -> None:
    state.updated_at = utc_now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    dump_yaml(
        {
            "job_id": state.job_id,
            "pipeline_id": state.pipeline_id,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "work_items": state.work_items,
            "cursor": state.cursor,
            "completed": state.completed,
            "notes": state.notes,
        },
        path,
    )


def run_planned_job(
    *,
    state_path: Path,
    job_id: str,
    pipeline_id: str,
    work_items: list[dict],
    item_id_fn: Callable[[dict], str],
    batch_size: int,
    execute_batch_fn: Callable[[list[dict]], list[str]],
    load_yaml: LoadFn,
    dump_yaml: DumpFn,
) -> JobState:
    """Run a planned job with checkpointing.

    - work_items MUST be stable and deterministic.
    - item_id_fn MUST be stable.
    - execute_batch_fn returns output paths written (strings) for bookkeeping.

    Resumes by loading state_path and skipping completed item_ids.
    """

    st = load_state(state_path, load_yaml=load_yaml)
    if st is None or st.job_id != job_id or st.pipeline_id != pipeline_id:
        st = JobState(job_id=job_id, pipeline_id=pipeline_id)
        st.work_items = work_items
        st.cursor = 0
        save_state(st, state_path, dump_yaml=dump_yaml)

    # Ensure plan is persisted (but do not overwrite existing completed map).
    if not st.work_items:
        st.work_items = work_items

    n = len(st.work_items)
    i = max(0, min(int(st.cursor or 0), n))

    while i < n:
        # Build next batch of not-yet-completed items
        batch: list[dict] = []
        j = i
        while j < n and len(batch) < max(1, int(batch_size)):
            item = st.work_items[j]
            iid = item_id_fn(item)
            if not st.is_completed(iid):
                batch.append(item)
            j += 1

        if not batch:
            # Nothing left in this segment; advance cursor
            i = j
            st.cursor = i
            save_state(st, state_path, dump_yaml=dump_yaml)
            continue

        outputs = execute_batch_fn(batch)
        # Mark items completed
        for item in batch:
            iid = item_id_fn(item)
            st.mark_completed(iid, outputs=outputs)

        # Advance cursor to where we scanned up to (j)
        i = j
        st.cursor = i
        save_state(st, state_path, dump_yaml=dump_yaml)

    return st
