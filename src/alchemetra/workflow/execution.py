"""Execution engine: runs a :class:`WorkflowGraph` against real data.

Responsibilities:

* For entry-point nodes (no incoming edges), use the externally supplied
  source artifact directly - no plugin lookup needed.
* For all other nodes, resolve ``plugin_id`` to a
  :class:`~alchemetra.workflow.node.NodeBase` subclass via the plugin
  registry, gather inputs from upstream nodes' outputs, and run it.
* Cache results keyed by (node id, params, input artifact ids) so that
  re-running after a downstream-only change is fast.
* Record everything in a
  :class:`~alchemetra.provenance.tracker.ProvenanceTracker`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from ..data.artifact import Artifact
from ..plugins.registry import PluginKind, PluginRegistry
from ..provenance.tracker import ProvenanceTracker
from .graph import GraphError, WorkflowGraph


def _hash_params(params: dict[str, Any]) -> str:
    encoded = json.dumps(params, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()


@dataclass
class ExecutionResult:
    """Result of running (part of) a workflow graph."""

    #: artifact id -> Artifact, for every artifact produced or reused.
    artifacts: dict[str, Artifact] = field(default_factory=dict)

    #: node id -> {output_port: artifact_id}, the "current" output of
    #: each (executed or entry-point) node.
    node_outputs: dict[str, dict[str, str]] = field(default_factory=dict)

    #: node ids that were actually (re-)executed, as opposed to served
    #: from cache or taken directly from source artifacts.
    executed_nodes: list[str] = field(default_factory=list)


class ExecutionEngine:
    """Runs a :class:`WorkflowGraph`, with caching and provenance."""

    #: Conventional name of the single output port of an entry-point
    #: (source) node.
    SOURCE_PORT = "out"

    def __init__(
        self,
        graph: WorkflowGraph,
        tracker: ProvenanceTracker | None = None,
    ) -> None:
        self.graph = graph
        self.tracker = tracker or ProvenanceTracker()

        # cache_key -> {output_port: Artifact}
        self._cache: dict[str, dict[str, Artifact]] = {}

    def invalidate(self, node_id: str) -> None:
        """Drop cached results for ``node_id`` and everything downstream
        of it - call this after a parameter edit."""

        for affected in self.graph.downstream_of(node_id):
            keys_to_drop = [
                key for key in self._cache if key.startswith(f"{affected}:")
            ]
            for key in keys_to_drop:
                del self._cache[key]

    def run(
        self,
        source_artifacts: dict[str, Artifact],
        target_nodes: list[str] | None = None,
    ) -> ExecutionResult:
        """Execute the graph (or the subgraph needed for ``target_nodes``).

        Parameters
        ----------
        source_artifacts:
            Artifacts to use for entry-point nodes (nodes with no
            incoming edges), keyed by node id.
        target_nodes:
            If given, only execute the nodes required to produce these
            (plus their dependencies); useful for "run up to here" in the
            UI. Defaults to the whole graph.
        """

        order = self.graph.topo_order()
        if target_nodes is not None:
            required: set[str] = set()
            for target in target_nodes:
                required |= self._ancestors(target)
                required.add(target)
            order = [n for n in order if n in required]

        result = ExecutionResult()

        for node_id in order:
            instance = self.graph.nodes[node_id]
            incoming = self.graph.incoming_edges(node_id)

            if not incoming:
                artifact = source_artifacts.get(node_id)
                if artifact is None:
                    raise GraphError(
                        f"No source artifact supplied for entry node "
                        f"'{node_id}'"
                    )
                result.node_outputs[node_id] = {self.SOURCE_PORT: artifact.id}
                result.artifacts[artifact.id] = artifact
                continue

            node_cls = PluginRegistry.get(
                PluginKind.PROCESSING_NODE, instance.plugin_id
            )
            params = node_cls.validate_params(instance.params)

            inputs = self._gather_inputs(node_id, result)
            input_ids = tuple(sorted(a.id for a in inputs.values()))
            cache_key = f"{node_id}:{_hash_params(params)}:{input_ids}"

            if cache_key in self._cache:
                outputs = self._cache[cache_key]
            else:
                node = node_cls()
                node.validate_inputs(inputs)
                outputs = node.run(inputs, params)
                for port_name, artifact in outputs.items():
                    artifact.produced_by = node_id
                    artifact.output_port = port_name
                    artifact.params_hash = _hash_params(params)
                self._cache[cache_key] = outputs
                self.tracker.record(
                    node_id=node_id,
                    plugin_id=instance.plugin_id,
                    params=params,
                    inputs={k: a.id for k, a in inputs.items()},
                    outputs={k: a.id for k, a in outputs.items()},
                )
                result.executed_nodes.append(node_id)

            result.node_outputs[node_id] = {
                port: artifact.id for port, artifact in outputs.items()
            }
            for artifact in outputs.values():
                result.artifacts[artifact.id] = artifact

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ancestors(self, node_id: str) -> set[str]:
        seen: set[str] = set()
        stack = [node_id]
        while stack:
            current = stack.pop()
            for edge in self.graph.incoming_edges(current):
                if edge.source_node not in seen:
                    seen.add(edge.source_node)
                    stack.append(edge.source_node)
        return seen

    def _gather_inputs(
        self, node_id: str, result: ExecutionResult
    ) -> dict[str, Artifact]:
        inputs: dict[str, Artifact] = {}

        for edge in self.graph.incoming_edges(node_id):
            source_outputs = result.node_outputs.get(edge.source_node)
            if source_outputs is None:
                raise GraphError(
                    f"Node '{edge.source_node}' has not been executed yet "
                    f"(out of order graph?)"
                )
            artifact_id = source_outputs[edge.source_port]
            inputs[edge.target_port] = result.artifacts[artifact_id]

        return inputs
