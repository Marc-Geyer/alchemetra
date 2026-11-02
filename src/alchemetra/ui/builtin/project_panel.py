"""Project explorer panel: a tree of raw data, derived data and results."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget

from ...data.artifact import Artifact
from ...plugins.registry import register_plugin
from ..context import UiContext
from ..panels.base import PanelPlugin

#: Qt.ItemDataRole slot used to stash an artifact id on a tree item.
_ARTIFACT_ID_ROLE = Qt.ItemDataRole.UserRole


@register_plugin
class ProjectExplorerPanel(PanelPlugin):
    """Tree view of the current project's data.

    Top-level groups mirror the project structure (Raw Data, Derived
    Data, Results). Selecting an artifact emits
    :attr:`UiContext.artifact_selected`; double-clicking it requests a
    view via :attr:`UiContext.view_requested`.
    """

    plugin_id = "core.panel.project_explorer"
    display_name = "Project"
    description = "Raw data, derived data and results in the current project."
    default_area = Qt.DockWidgetArea.LeftDockWidgetArea

    def create_widget(self, context: UiContext) -> QWidget:
        tree = QTreeWidget()
        tree.setHeaderHidden(True)

        def refresh() -> None:
            tree.clear()
            project = context.project

            raw_group = QTreeWidgetItem(["Raw Data"])
            for node_id, artifact in project.raw_data.items():
                _add_artifact_item(raw_group, artifact, extra=f" ({node_id})")
            tree.addTopLevelItem(raw_group)

            derived_group = QTreeWidgetItem(["Derived Data"])
            raw_ids = {artifact.id for artifact in project.raw_data.values()}
            for artifact in project.derived_data.values():
                if artifact.id in raw_ids:
                    continue
                _add_artifact_item(derived_group, artifact)
            tree.addTopLevelItem(derived_group)

            results_group = QTreeWidgetItem(["Results"])
            for name in project.results:
                results_group.addChild(QTreeWidgetItem([name]))
            tree.addTopLevelItem(results_group)

            tree.expandAll()

        def on_item_clicked(item: QTreeWidgetItem, _column: int) -> None:
            artifact_id = item.data(0, _ARTIFACT_ID_ROLE)
            if artifact_id:
                context.select_artifact(artifact_id)

        def on_item_double_clicked(item: QTreeWidgetItem, _column: int) -> None:
            artifact_id = item.data(0, _ARTIFACT_ID_ROLE)
            if artifact_id:
                context.request_view(artifact_id)

        tree.itemClicked.connect(on_item_clicked)
        tree.itemDoubleClicked.connect(on_item_double_clicked)
        context.project_changed.connect(refresh)
        context.workflow_changed.connect(refresh)

        refresh()
        return tree


def _add_artifact_item(
    parent: QTreeWidgetItem, artifact: Artifact, extra: str = ""
) -> QTreeWidgetItem:
    item = QTreeWidgetItem([f"{artifact.label}{extra}"])
    item.setData(0, _ARTIFACT_ID_ROLE, artifact.id)
    parent.addChild(item)
    return item
