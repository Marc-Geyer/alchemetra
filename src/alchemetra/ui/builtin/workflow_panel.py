"""Workflow panel: lists the nodes/edges of the current project's
workflow graph and lets the user run it.

This is a minimal, list-based stand-in for a full graphical node editor.
It exposes the same underlying
:class:`~alchemetra.workflow.graph.WorkflowGraph` that a future
drag-and-drop editor would operate on, so it can be swapped out later
without changing how :class:`~alchemetra.project.project.Project` or
:class:`~alchemetra.ui.context.UiContext` are used.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...plugins.registry import register_plugin
from ..context import UiContext
from ..panels.base import PanelPlugin


@register_plugin
class WorkflowPanel(PanelPlugin):
    """List view of workflow nodes/edges plus a "Run workflow" button."""

    plugin_id = "core.panel.workflow"
    display_name = "Workflow"
    description = "Nodes and connections of the current processing workflow."
    default_area = Qt.DockWidgetArea.BottomDockWidgetArea

    def create_widget(self, context: UiContext) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        node_list = QListWidget()
        run_button = QPushButton("Run workflow")

        layout.addWidget(node_list)
        layout.addWidget(run_button)

        def refresh() -> None:
            node_list.clear()
            graph = context.project.workflow
            for node_id in _safe_order(graph):
                node = graph.nodes[node_id]
                incoming = graph.incoming_edges(node_id)
                kind = "entry point" if not incoming else f"{len(incoming)} input(s)"
                node_list.addItem(
                    QListWidgetItem(f"{node.id}  -  {node.plugin_id}  ({kind})")
                )

        def run_workflow() -> None:
            try:
                context.project.run()
            except Exception as exc:  # noqa: BLE001 - surface to the user
                QMessageBox.critical(container, "Workflow failed", str(exc))
                return
            context.notify_workflow_changed()

        run_button.clicked.connect(run_workflow)
        context.project_changed.connect(refresh)
        context.workflow_changed.connect(refresh)

        refresh()
        return container


def _safe_order(graph) -> list[str]:
    """Topological order if possible, otherwise insertion order (so the
    panel still shows something useful for a graph with a cycle while
    the user fixes it)."""

    try:
        return graph.topo_order()
    except Exception:  # noqa: BLE001
        return list(graph.nodes)
