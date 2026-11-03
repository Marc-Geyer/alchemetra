"""Provenance records: who produced what, from what, with which settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class LineageRecord:
    """One execution of one node, linking its inputs to its outputs."""

    node_id: str
    plugin_id: str
    params: dict[str, Any]

    #: input port name -> artifact id
    inputs: dict[str, str]

    #: output port name -> artifact id
    outputs: dict[str, str]

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "plugin_id": self.plugin_id,
            "params": self.params,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineageRecord":
        return cls(
            node_id=data["node_id"],
            plugin_id=data["plugin_id"],
            params=data["params"],
            inputs=data["inputs"],
            outputs=data["outputs"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )
