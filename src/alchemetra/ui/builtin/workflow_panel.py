"""Workflow panel: nodes in execution order with add / remove / run."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...plugins.base import PluginKind
from ...plugins.registry import PluginRegistry, register_plugin
from ..context import UiContext
from ..panels.base import PanelPlugin

_NODE_ID_ROLE = Qt.ItemDataRole.UserRole


class WorkflowWidget(QWidget):
    """List of workflow nodes in execution order.

    "Add node" appends a processing node after the selected node (connecting
    output to input automatically). Selecting a node emits
    ``UiContext.node_selected`` so inspectors can show its parameters.
    """

    def __init__(self, context: UiContext) -> None:
        super().__init__()
        self.context = context
        self._list = QListWidget()
        add_btn, remove_btn, run_btn = (
            QPushButton("Add node\u2026"),
            QPushButton("Remove"),
            QPushButton("Run workflow"),
        )
        buttons = QHBoxLayout()
        for b in (add_btn, remove_btn, run_btn):
            buttons.addWidget(b)
        layout = QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.addLayout(buttons)

        self._list.currentItemChanged.connect(self._on_current_changed)
        add_btn.clicked.connect(self._add_dialog)
        remove_btn.clicked.connect(lambda: self._guard("Remove failed", self.remove_selected))
        run_btn.clicked.connect(lambda: self._guard("Workflow failed", self.run_workflow))
        context.project_changed.connect(self.refresh)
        context.workflow_changed.connect(self.refresh)
        self.refresh()

    # -- selection ------------------------------------------------------
    def selected_node_id(self) -> str | None:
        item = self._list.currentItem()
        return item.data(_NODE_ID_ROLE) if item else None

    def select(self, node_id: str) -> None:
        self._list.blockSignals(True)
        for row in range(self._list.count()):
            if self._list.item(row).data(_NODE_ID_ROLE) == node_id:
                self._list.setCurrentRow(row)
        self._list.blockSignals(False)
        self.context.select_node(node_id)

    def _on_current_changed(self, current, _previous) -> None:
        if current is not None:
            self.context.select_node(current.data(_NODE_ID_ROLE))

    # -- actions (raise on error; wrapped by _guard for the buttons) ------
    def add_node(self, plugin_id: str) -> None:
        node = self.context.project.add_processing_node(plugin_id, after=self.selected_node_id())
        self.context.notify_workflow_changed()
        self.select(node.id)

    def remove_selected(self) -> None:
        node_id = self.selected_node_id()
        if node_id is None:
            return
        self.context.project.remove_node(node_id)
        self.context.notify_workflow_changed()

    def run_workflow(self) -> None:
        self.context.project.run()
        self.context.notify_workflow_changed()

    # -- dialogs / helpers ----------------------------------------------
    def _add_dialog(self) -> None:
        plugins = {
            (p.display_name or p.plugin_id): p.plugin_id
            for p in PluginRegistry.all(PluginKind.PROCESSING_NODE)
        }
        name, ok = QInputDialog.getItem(self, "Add node", "Processing step:", sorted(plugins), 0, False)
        if ok:
            self._guard("Add node failed", lambda: self.add_node(plugins[name]))

    def _guard(self, title: str, action) -> None:
        try:
            action()
        except Exception as exc:  # noqa: BLE001 - surface to the user
            QMessageBox.critical(self, title, str(exc))

    def refresh(self) -> None:
        keep = self.selected_node_id()
        graph = self.context.project.workflow
        try:
            order = graph.topo_order()
        except Exception:  # noqa: BLE001 - still show nodes while a cycle is fixed
            order = list(graph.nodes)
        self._list.blockSignals(True)
        self._list.clear()
        for node_id in order:
            node = graph.nodes[node_id]
            kind = "entry" if node_id in self.context.project.raw_data else f"{len(graph.incoming_edges(node_id))} input(s)"
            item = QListWidgetItem(f"{node.id}  ·  {node.plugin_id}  ({kind})")
            item.setData(_NODE_ID_ROLE, node_id)
            self._list.addItem(item)
            if node_id == keep:
                self._list.setCurrentItem(item)
        self._list.blockSignals(False)


@register_plugin
class WorkflowPanel(PanelPlugin):
    plugin_id = "core.panel.workflow"
    display_name = "Workflow"
    description = "Nodes of the current processing workflow; add, remove and run steps."
    default_area = Qt.DockWidgetArea.BottomDockWidgetArea

    def create_widget(self, context: UiContext) -> QWidget:
        return WorkflowWidget(context)
