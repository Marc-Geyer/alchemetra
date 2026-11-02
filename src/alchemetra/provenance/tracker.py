"""Provenance tracker: an append-only log of workflow executions.

The tracker is intentionally decoupled from the execution engine's cache
- the cache may be cleared (e.g. on app restart) while the provenance log
persists with the project, so users can always answer "how was this
artifact produced?" even for results that are no longer cached in memory.
"""

from __future__ import annotations

from typing import Any

from .lineage import LineageRecord


class ProvenanceTracker:
    def __init__(self) -> None:
        self.records: list[LineageRecord] = []

        # artifact id -> the record that produced it, for fast lookups.
        self._producer: dict[str, LineageRecord] = {}

    def record(
        self,
        node_id: str,
        plugin_id: str,
        params: dict[str, Any],
        inputs: dict[str, str],
        outputs: dict[str, str],
    ) -> LineageRecord:
        record = LineageRecord(
            node_id=node_id,
            plugin_id=plugin_id,
            params=params,
            inputs=inputs,
            outputs=outputs,
        )
        self.records.append(record)
        for artifact_id in outputs.values():
            self._producer[artifact_id] = record
        return record

    def producer_of(self, artifact_id: str) -> LineageRecord | None:
        return self._producer.get(artifact_id)

    def lineage_of(self, artifact_id: str) -> list[LineageRecord]:
        """Return the full chain of records that led to ``artifact_id``,
        oldest first."""

        chain: list[LineageRecord] = []
        seen_artifacts = {artifact_id}
        frontier = [artifact_id]

        while frontier:
            current = frontier.pop()
            record = self._producer.get(current)
            if record is None or record in chain:
                continue
            chain.append(record)
            for input_artifact_id in record.inputs.values():
                if input_artifact_id not in seen_artifacts:
                    seen_artifacts.add(input_artifact_id)
                    frontier.append(input_artifact_id)

        chain.reverse()
        return chain

    # ------------------------------------------------------------------
    # Serialisation (project files)
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {"records": [r.to_dict() for r in self.records]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProvenanceTracker":
        tracker = cls()
        for record_data in data.get("records", []):
            record = LineageRecord.from_dict(record_data)
            tracker.records.append(record)
            for artifact_id in record.outputs.values():
                tracker._producer[artifact_id] = record
        return tracker
