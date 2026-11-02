"""A directed connection between two node ports in a workflow graph."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Edge:
    source_node: str
    source_port: str
    target_node: str
    target_port: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source_node": self.source_node,
            "source_port": self.source_port,
            "target_node": self.target_node,
            "target_port": self.target_port,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Edge":
        return cls(**data)
