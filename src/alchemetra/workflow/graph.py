"""The workflow graph: a serialisable DAG of node instances and edges.

This is the data structure behind both the interactive workflow editor
and exported "processing templates". A template is exactly the JSON-ish
dict produced by :meth:`WorkflowGraph.to_template` - re-loading it with
:meth:`WorkflowGraph.from_template` reconstructs an identical graph,
ready to be executed by
:class:`alchemetra.workflow.execution.ExecutionEngine`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from .edge import Edge


class GraphError(Exception):
    """Raised for structural problems: missing nodes, cycles, ..."""


@dataclass
class NodeInstance:
    """One placed instance of a :class:`~alchemetra.workflow.node.NodeBase`
    plugin within a graph.

    Nodes with no incoming edges are *entry points*: when the graph is
    executed, their output is taken directly from the externally supplied
    source artifacts (see
    :meth:`alchemetra.workflow.execution.ExecutionEngine.run`) rather than
    by resolving ``plugin_id`` against the processing-node registry. For
    such nodes, ``plugin_id`` is purely descriptive (e.g. the data source
    plugin that originally produced the data) and may reference the
    ``DATA_SOURCE`` registry instead of ``PROCESSING_NODE``.
    """

    id: str
    plugin_id: str
    params: dict[str, Any] = field(default_factory=dict)

    #: UI layout hint (canvas position); ignored for execution.
    position: tuple[float, float] = (0.0, 0.0)

    #: Free-form per-instance metadata, e.g. a user-given title.
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "plugin_id": self.plugin_id,
            "params": self.params,
            "position": list(self.position),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NodeInstance":
        return cls(
            id=data["id"],
            plugin_id=data["plugin_id"],
            params=dict(data.get("params", {})),
            position=tuple(data.get("position", (0.0, 0.0))),
            metadata=dict(data.get("metadata", {})),
        )


class WorkflowGraph:
    """A DAG of :class:`NodeInstance` connected by :class:`Edge`.

    The graph itself knows nothing about plugin *behaviour* - it is pure
    structure plus validation/serialisation. Resolving ``plugin_id`` to
    an actual node class happens in
    :mod:`alchemetra.workflow.execution`, keeping this module independent
    of the plugin registry (useful for tests / tooling that only need to
    inspect or edit graph structure).
    """

    TEMPLATE_VERSION: ClassVar[int] = 1

    def __init__(self) -> None:
        self.nodes: dict[str, NodeInstance] = {}
        self.edges: list[Edge] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------
    def add_node(self, node: NodeInstance) -> NodeInstance:
        if node.id in self.nodes:
            raise GraphError(f"Node id '{node.id}' already exists")
        self.nodes[node.id] = node
        return node

    def remove_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            raise GraphError(f"Unknown node '{node_id}'")

        self.edges = [
            e
            for e in self.edges
            if e.source_node != node_id and e.target_node != node_id
        ]
        del self.nodes[node_id]

    def connect(
        self,
        source_node: str,
        source_port: str,
        target_node: str,
        target_port: str,
    ) -> Edge:
        for node_id in (source_node, target_node):
            if node_id not in self.nodes:
                raise GraphError(f"Unknown node '{node_id}'")

        edge = Edge(source_node, source_port, target_node, target_port)
        if edge in self.edges:
            return edge

        self.edges.append(edge)
        try:
            self.topo_order()
        except GraphError:
            self.edges.remove(edge)
            raise
        return edge

    def disconnect(self, edge: Edge) -> None:
        self.edges.remove(edge)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def incoming_edges(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.target_node == node_id]

    def outgoing_edges(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.source_node == node_id]

    def topo_order(self) -> list[str]:
        """Return node ids in an order valid for execution.

        Raises :class:`GraphError` if the graph contains a cycle.
        """

        in_degree = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            in_degree[edge.target_node] += 1

        ready = [n for n, d in in_degree.items() if d == 0]
        order: list[str] = []

        while ready:
            ready.sort()  # deterministic ordering
            node_id = ready.pop(0)
            order.append(node_id)
            for edge in self.outgoing_edges(node_id):
                in_degree[edge.target_node] -= 1
                if in_degree[edge.target_node] == 0:
                    ready.append(edge.target_node)

        if len(order) != len(self.nodes):
            raise GraphError("Workflow graph contains a cycle")
        return order

    def downstream_of(self, node_id: str) -> set[str]:
        """All nodes reachable from ``node_id`` (inclusive).

        Used to figure out what needs re-running after a parameter
        change (see
        :meth:`alchemetra.workflow.execution.ExecutionEngine.invalidate`).
        """

        seen = {node_id}
        stack = [node_id]
        while stack:
            current = stack.pop()
            for edge in self.outgoing_edges(current):
                if edge.target_node not in seen:
                    seen.add(edge.target_node)
                    stack.append(edge.target_node)
        return seen

    # ------------------------------------------------------------------
    # Templates (serialisation)
    # ------------------------------------------------------------------
    def to_template(self) -> dict[str, Any]:
        """Export this graph as a plain dict, suitable for ``json.dump``.

        This *is* the "processing template" the platform promises can be
        exported at any time: a complete, re-runnable description of
        every processing step and its parameters.
        """

        return {
            "template_version": self.TEMPLATE_VERSION,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_template(cls, data: dict[str, Any]) -> "WorkflowGraph":
        version = data.get("template_version")
        if version != cls.TEMPLATE_VERSION:
            # Hook for future migrations: translate older templates here
            # before continuing. For now we proceed best-effort.
            pass

        graph = cls()
        for node_data in data.get("nodes", []):
            graph.add_node(NodeInstance.from_dict(node_data))
        for edge_data in data.get("edges", []):
            edge = Edge.from_dict(edge_data)
            graph.edges.append(edge)
        graph.topo_order()  # validate: raises if the template has a cycle
        return graph
