"""Node inspector: parameter editor for the node selected in the workflow panel."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ...plugins.base import PluginKind
from ...plugins.registry import PluginRegistry, register_plugin
from ..context import UiContext
from ..panels.base import PanelPlugin
from ..widgets.parameter_form import ParameterForm


class NodeInspectorWidget(QWidget):
    def __init__(self, context: UiContext) -> None:
        super().__init__()
        self.context = context
        self._node_id: str | None = None
        self._form: ParameterForm | None = None
        self._title = QLabel("No node selected")
        self._title.setWordWrap(True)
        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self._title)
        self._layout.addStretch(1)
        context.node_selected.connect(self.show_node)
        context.project_changed.connect(lambda: self.show_node(None))
        context.workflow_changed.connect(self._on_workflow_changed)

    def show_node(self, node_id: str | None) -> None:
        if self._form is not None:
            self._form.setParent(None)
            self._form.deleteLater()
            self._form = None
        project = self.context.project
        node = project.workflow.nodes.get(node_id) if node_id else None
        self._node_id = node.id if node else None
        if node is None:
            self._title.setText("No node selected")
            return
        if node.id in project.raw_data:
            self._title.setText(f"<b>{node.id}</b><br>Entry node – source data, no parameters.")
            return
        try:
            plugin_cls = PluginRegistry.get(PluginKind.PROCESSING_NODE, node.plugin_id)
        except KeyError:
            self._title.setText(f"<b>{node.id}</b><br>Plugin '{node.plugin_id}' is not installed.")
            return
        self._title.setText(f"<b>{plugin_cls.display_name}</b> ({node.id})<br>{plugin_cls.description}")
        if plugin_cls.parameters:
            self._form = ParameterForm(plugin_cls.parameters, node.params)
            self._form.values_changed.connect(self._on_values_changed)
            self._layout.insertWidget(1, self._form)

    def _on_values_changed(self, values: dict) -> None:
        try:
            self.context.project.set_node_params(self._node_id, values)
        except Exception as exc:  # noqa: BLE001 - show validation errors inline
            self._title.setText(f"<span style='color:#c00'>{exc}</span>")
            return
        self.context.notify_workflow_changed()

    def _on_workflow_changed(self) -> None:
        if self._node_id and self._node_id not in self.context.project.workflow.nodes:
            self.show_node(None)


@register_plugin
class NodeInspectorPanel(PanelPlugin):
    plugin_id = "core.panel.node_inspector"
    display_name = "Node Parameters"
    description = "Edit the parameters of the selected workflow node."
    default_area = Qt.DockWidgetArea.RightDockWidgetArea

    def create_widget(self, context: UiContext) -> QWidget:
        return NodeInspectorWidget(context)
