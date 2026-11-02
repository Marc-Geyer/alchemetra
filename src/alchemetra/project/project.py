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
from ..provenance.tracker import ProvenanceTracker
from ..workflow.execution import ExecutionEngine, ExecutionResult
from ..workflow.graph import WorkflowGraph


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

    # ------------------------------------------------------------------
    def run(self, target_nodes: list[str] | None = None) -> ExecutionResult:
        """Execute the workflow graph against the project's raw data."""

        engine = ExecutionEngine(self.workflow, tracker=self.provenance)
        result = engine.run(self.raw_data, target_nodes=target_nodes)
        self.derived_data.update(result.artifacts)
        return result

    def add_annotation(self, annotation: AnnotationBase) -> None:
        self.annotations.append(annotation)

    def remove_annotation(self, annotation_id: str) -> None:
        self.annotations = [
            a for a in self.annotations if a.id != annotation_id
        ]

    def annotations_for(self, artifact_id: str) -> list[AnnotationBase]:
        return [a for a in self.annotations if a.artifact_id == artifact_id]

    def export_template(self) -> dict[str, Any]:
        """Export just the workflow as a re-usable processing template
        (see :meth:`WorkflowGraph.to_template`)."""

        return self.workflow.to_template()

    def import_template(self, template: dict[str, Any]) -> None:
        self.workflow = WorkflowGraph.from_template(template)
