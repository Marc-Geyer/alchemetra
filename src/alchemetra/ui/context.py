"""Shared observable state for the running UI – the dependency boundary for plugins."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from ..data.artifact import Artifact
from ..project.project import Project
from ..services.annotation_service import AnnotationService


class UiContext(QObject):
    """Holds the current Project and forwards change signals.

    Panel and view plugins depend on this class only – never on MainWindow.
    """

    project_changed = Signal()
    workflow_changed = Signal()
    annotations_changed = Signal(object, str)
    artifact_selected = Signal(str)
    view_requested = Signal(str)
    node_selected = Signal(str)   # workflow node id

    def __init__(self, project: Project | None = None) -> None:
        super().__init__()
        self._project = project or Project()
        self._annotation_service = AnnotationService(self._project)
        self._annotation_service.on_change(
            lambda ann, kind: self.annotations_changed.emit(ann, kind)
        )

    @property
    def project(self) -> Project:
        return self._project

    @property
    def annotation_service(self) -> AnnotationService:
        return self._annotation_service

    def set_project(self, project: Project) -> None:
        self._project = project
        self._annotation_service = AnnotationService(self._project)
        self._annotation_service.on_change(
            lambda ann, kind: self.annotations_changed.emit(ann, kind)
        )
        self.project_changed.emit()
        self.workflow_changed.emit()

    def artifact(self, artifact_id: str) -> Artifact | None:
        """Convenience lookup across raw and derived data."""

        for artifact in self._project.raw_data.values():
            if artifact.id == artifact_id:
                return artifact
        return self._project.derived_data.get(artifact_id)

    def all_artifacts(self) -> dict[str, Artifact]:
        """All artifacts keyed by artifact id."""
        artifacts = {a.id: a for a in self._project.raw_data.values()}
        artifacts.update(self._project.derived_data)
        return artifacts

    def select_artifact(self, artifact_id: str) -> None:
        self.artifact_selected.emit(artifact_id)

    def select_node(self, node_id: str) -> None:
        self.node_selected.emit(node_id)

    def request_view(self, artifact_id: str) -> None:
        self.view_requested.emit(artifact_id)

    def notify_workflow_changed(self) -> None:
        self.workflow_changed.emit()
