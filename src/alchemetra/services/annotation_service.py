"""Annotation service: a thin facade over
:class:`alchemetra.project.project.Project` annotations.

The UI (annotation panels, overlay renderers in the plot widgets) should
go through this service rather than poking ``project.annotations``
directly. This gives a single place to:

* keep annotation lookups by artifact / axis role fast and consistent;
* notify listeners (e.g. an open plot widget) when annotations change,
  without the project model needing to know anything about the UI.
"""

from __future__ import annotations

from typing import Callable

from ..annotations.base import AnnotationBase
from ..data.dataset import AxisRole
from ..project.project import Project

#: A listener is called with the annotation that changed and the kind of
#: change ("added" or "removed").
Listener = Callable[[AnnotationBase, str], None]


class AnnotationService:
    """Add/remove/query annotations on a :class:`Project`, with change
    notifications.

    Example
    -------
    >>> service = AnnotationService(project)
    >>> unsubscribe = service.on_change(lambda ann, kind: refresh_plot())
    >>> service.add(PeakAnnotation(artifact_id=artifact.id, position=1350.0,
    ...                             width=20.0))
    """

    def __init__(self, project: Project) -> None:
        self.project = project
        self._listeners: list[Listener] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------
    def add(self, annotation: AnnotationBase) -> AnnotationBase:
        self.project.add_annotation(annotation)
        self._notify(annotation, "added")
        return annotation

    def remove(self, annotation_id: str) -> None:
        annotation = self.get(annotation_id)
        if annotation is None:
            return
        self.project.remove_annotation(annotation_id)
        self._notify(annotation, "removed")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get(self, annotation_id: str) -> AnnotationBase | None:
        for annotation in self.project.annotations:
            if annotation.id == annotation_id:
                return annotation
        return None

    def for_artifact(self, artifact_id: str) -> list[AnnotationBase]:
        """All annotations created on ``artifact_id``.

        Equivalent to :meth:`Project.annotations_for`, exposed here for
        symmetry with :meth:`by_role`.
        """

        return self.project.annotations_for(artifact_id)

    def by_role(self, role: AxisRole) -> list[AnnotationBase]:
        """All annotations whose :meth:`AnnotationBase.axis_roles`
        includes ``role``.

        Used by axis-role-aware widgets (e.g. a spectral slice view
        showing only peak annotations, regardless of which artifact or
        domain they came from) to find relevant annotations without any
        domain-specific filtering.
        """

        return [
            annotation
            for annotation in self.project.annotations
            if role in annotation.axis_roles()
        ]

    # ------------------------------------------------------------------
    # Change notification
    # ------------------------------------------------------------------
    def on_change(self, listener: Listener) -> Callable[[], None]:
        """Register ``listener`` to be called on every :meth:`add` /
        :meth:`remove`.

        Returns an "unsubscribe" callable.
        """

        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def _notify(self, annotation: AnnotationBase, kind: str) -> None:
        for listener in list(self._listeners):
            listener(annotation, kind)
