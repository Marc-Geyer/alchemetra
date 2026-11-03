"""The Project: top-level container tying data, workflow, annotations and
results together.

Mirrors the structure described in the project README::

    Project
     - Raw Data
     - Derived Data
     - Workflow
     - User Annotations
     - Results
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..annotations.base import AnnotationBase
from ..data.artifact import Artifact
from ..plugins.base import PluginKind
from ..plugins.registry import PluginRegistry
from ..provenance.tracker import ProvenanceTracker
from ..workflow.execution import ExecutionEngine, ExecutionResult
from ..workflow.graph import NodeInstance, WorkflowGraph


@dataclass
class Project:
    name: str = "Untitled project"

    #: Artifacts imported directly via data sources (no producing node in
    #: the workflow graph). Keyed by the id of the corresponding
    #: entry-point node in :attr:`workflow`.
    raw_data: dict[str, Artifact] = field(default_factory=dict)

    #: All artifacts produced by the most recent :meth:`run`, including
    #: raw data, keyed by artifact id.
    derived_data: dict[str, Artifact] = field(default_factory=dict)

    workflow: WorkflowGraph = field(default_factory=WorkflowGraph)

    annotations: list[AnnotationBase] = field(default_factory=list)

    #: Free-form bag for "results" produced explicitly by the user, e.g.
    #: exported figures or fit reports - distinct from intermediate
    #: workflow artifacts.
    results: dict[str, Any] = field(default_factory=dict)

    provenance: ProvenanceTracker = field(default_factory=ProvenanceTracker)

    _engine: ExecutionEngine | None = field(default=None, init=False, repr=False)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def run(self, target_nodes: list[str] | None = None) -> ExecutionResult:
        """Execute the workflow graph against the project's raw data."""

        # One engine per workflow so the node cache survives repeated runs.
        if self._engine is None or self._engine.graph is not self.workflow:
            self._engine = ExecutionEngine(self.workflow, tracker=self.provenance)
        result = self._engine.run(self.raw_data, target_nodes=target_nodes)
        self.derived_data.update(result.artifacts)
        return result

    # ------------------------------------------------------------------
    # Raw data
    # ------------------------------------------------------------------
    def unique_node_id(self, base: str) -> str:
        candidate, n = base, 2
        while candidate in self.workflow.nodes or candidate in self.raw_data:
            candidate = f"{base}_{n}"
            n += 1
        return candidate

    def add_raw_data(self, node_id: str, artifact: Artifact,
                     plugin_id: str = "core.source.imported") -> NodeInstance:
        """Register raw data and create the workflow entry node for it."""

        if node_id in self.raw_data or node_id in self.workflow.nodes:
            raise ValueError(f"Node id '{node_id}' already exists")
        node = self.workflow.add_node(NodeInstance(id=node_id, plugin_id=plugin_id))
        self.raw_data[node_id] = artifact
        return node

    # ------------------------------------------------------------------
    # Workflow editing
    # ------------------------------------------------------------------
    def _output_port(self, node_id: str) -> str:
        if node_id in self.raw_data:                      # entry node
            return ExecutionEngine.SOURCE_PORT
        node = self.workflow.nodes[node_id]
        ports = PluginRegistry.get(
            PluginKind.PROCESSING_NODE, node.plugin_id
        ).output_ports
        if not ports:
            raise ValueError(f"Node '{node_id}' has no output port")
        return ports[0].name

    def _drop_derived(self, node_ids: set[str]) -> None:
        self.derived_data = {
            k: a
            for k, a in self.derived_data.items()
            if a.produced_by not in node_ids
        }

    def add_processing_node(
        self,
        plugin_id: str,
        after: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> NodeInstance:
        """Add a processing node; if ``after`` is given, connect that
        node's (first) output to the new node's first input."""

        plugin = PluginRegistry.get(PluginKind.PROCESSING_NODE, plugin_id)()
        if after is not None:
            if after not in self.workflow.nodes:
                raise ValueError(f"Node '{after}' does not exist")
            if not plugin.input_ports:
                raise ValueError(f"'{plugin.display_name}' has no input port")
            source_port = self._output_port(after)

        node = NodeInstance(
            id=self.unique_node_id(plugin_id.rsplit(".", 1)[-1]),
            plugin_id=plugin_id,
            params=plugin.validate_params(params or {}),
        )
        self.workflow.add_node(node)
        if after is not None:
            try:
                self.workflow.connect(
                    after, source_port, node.id, plugin.input_ports[0].name
                )
            except Exception:
                self.workflow.remove_node(node.id)
                raise
        return node

    def remove_node(self, node_id: str) -> None:
        """Remove a processing node; derived data of it and everything
        downstream is dropped (it is stale)."""

        if node_id not in self.workflow.nodes:
            raise ValueError(f"Node '{node_id}' does not exist")
        if node_id in self.raw_data:
            raise ValueError("Entry nodes hold raw data and cannot be removed here")
        affected = {node_id, *self.workflow.downstream_of(node_id)}
        if self._engine is not None:
            self._engine.invalidate(node_id)
        self.workflow.remove_node(node_id)
        self._drop_derived(affected)

    def set_node_params(self, node_id: str, params: dict[str, Any]) -> None:
        """Validate and apply new parameters; stale derived data is dropped."""

        node = self.workflow.nodes[node_id]
        if node_id in self.raw_data:
            raise ValueError("Entry nodes have no parameters")
        plugin = PluginRegistry.get(PluginKind.PROCESSING_NODE, node.plugin_id)()
        merged = plugin.validate_params({**node.params, **params})
        if merged == node.params:
            return
        if self._engine is not None:
            self._engine.invalidate(node_id)
        node.params = merged
        self._drop_derived({node_id, *self.workflow.downstream_of(node_id)})

    # ------------------------------------------------------------------
    # Annotations
    # ------------------------------------------------------------------
    def add_annotation(self, annotation: AnnotationBase) -> None:
        self.annotations.append(annotation)

    def remove_annotation(self, annotation_id: str) -> None:
        self.annotations = [
            a for a in self.annotations if a.id != annotation_id
        ]

    def annotations_for(self, artifact_id: str) -> list[AnnotationBase]:
        return [a for a in self.annotations if a.artifact_id == artifact_id]

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------
    def export_template(self) -> dict[str, Any]:
        """Export just the workflow as a re-usable processing template
        (see :meth:`WorkflowGraph.to_template`)."""

        return self.workflow.to_template()

    def import_template(self, template: dict[str, Any]) -> None:
        self.workflow = WorkflowGraph.from_template(template)
