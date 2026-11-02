"""Shared context object passed to every panel and view plugin.

Panels and views must not reach into :class:`MainWindow` internals or
into each other directly - everything they need to read or react to
goes through :class:`UiContext`. This is what keeps panel/view plugins
decoupled from each other and from the main window implementation, so
third-party plugins only need to depend on this module plus the core
data model.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from ..data.artifact import Artifact
from ..project.project import Project
from ..services.annotation_service import AnnotationService


class UiContext(QObject):
    """Shared, observable state for the running application.

    Holds the current :class:`~alchemetra.project.project.Project` and
    the :class:`~alchemetra.services.annotation_service.AnnotationService`
    bound to it, plus Qt signals panels/views can connect to instead of
    polling.

    Panels/views that want to *cause* something to happen (open a view
    for an artifact, select a node in the workflow editor, ...) call the
    corresponding ``request_*`` method; :class:`MainWindow` connects to
    these once at startup and performs the actual UI action. This keeps
    the dependency direction one-way: plugins depend on
    :class:`UiContext`, never on :class:`MainWindow`.
    """

    #: Emitted whenever :attr:`project` is replaced (new/opened project).
    project_changed = Signal()

    #: Emitted after :attr:`project`'s workflow graph or its derived data
    #: changes (e.g. after a run). Panels showing workflow/result state
    #: should refresh on this signal.
    workflow_changed = Signal()

    #: Emitted by :class:`AnnotationService` callbacks, forwarded here so
    #: panels/views only need one signal to connect to.
    annotations_changed = Signal(object, str)  # (AnnotationBase, "added"|"removed")

    #: Emitted when the user selects an artifact in some panel (e.g. the
    #: project explorer). Views interested in "the currently selected
    #: artifact" connect to this.
    artifact_selected = Signal(str)  # artifact id

    #: Emitted to ask the main window to open a view for an artifact.
    view_requested = Signal(str)  # artifact id

    def __init__(self, project: Project | None = None) -> None:
        super().__init__()
        self._project = project or Project()
        self._annotation_service = AnnotationService(self._project)
        self._annotation_service.on_change(
            lambda annotation, kind: self.annotations_changed.emit(annotation, kind)
        )

    # ------------------------------------------------------------------
    @property
    def project(self) -> Project:
        return self._project

    @property
    def annotation_service(self) -> AnnotationService:
        return self._annotation_service

    def set_project(self, project: Project) -> None:
        """Replace the current project (e.g. after opening a project
        file) and notify everyone."""

        self._project = project
        self._annotation_service = AnnotationService(self._project)
        self._annotation_service.on_change(
            lambda annotation, kind: self.annotations_changed.emit(annotation, kind)
        )
        self.project_changed.emit()
        self.workflow_changed.emit()

    def artifact(self, artifact_id: str) -> Artifact | None:
        """Convenience lookup across raw and derived data."""

        return self._project.raw_data.get(artifact_id) or self._project.derived_data.get(
            artifact_id
        )

    def all_artifacts(self) -> dict[str, Artifact]:
        artifacts: dict[str, Artifact] = {}
        artifacts.update(self._project.raw_data)
        artifacts.update(self._project.derived_data)
        return artifacts

    # ------------------------------------------------------------------
    # Requests from panels/views to the main window
    # ------------------------------------------------------------------
    def select_artifact(self, artifact_id: str) -> None:
        self.artifact_selected.emit(artifact_id)

    def request_view(self, artifact_id: str) -> None:
        self.view_requested.emit(artifact_id)

    def notify_workflow_changed(self) -> None:
        self.workflow_changed.emit()
