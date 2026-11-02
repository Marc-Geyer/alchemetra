"""Properties panel: shows axis-role metadata for the selected artifact.

This panel is intentionally domain-agnostic - it just lists whatever
axes/variables the selected artifact's dataset has and the
:class:`~alchemetra.data.dataset.AxisRole` tags attached to each, plus
basic provenance (which node produced it, if any).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ...data.artifact import Artifact
from ...plugins.registry import register_plugin
from ..context import UiContext
from ..panels.base import PanelPlugin


@register_plugin
class PropertiesPanel(PanelPlugin):
    """Axis metadata and provenance info for the currently selected
    artifact."""

    plugin_id = "core.panel.properties"
    display_name = "Properties"
    description = "Axis roles, units and provenance for the selected artifact."
    default_area = Qt.DockWidgetArea.RightDockWidgetArea

    def create_widget(self, context: UiContext) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        title = QLabel("No artifact selected")
        title.setWordWrap(True)

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Axis", "Role", "Unit", "Label"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)

        layout.addWidget(title)
        layout.addWidget(table)

        def show_artifact(artifact_id: str) -> None:
            artifact = context.artifact(artifact_id)
            table.setRowCount(0)
            if artifact is None:
                title.setText("No artifact selected")
                return

            title.setText(_describe(artifact))

            axis_meta = artifact.dataset.axis_meta_dict()
            table.setRowCount(len(axis_meta))
            for row, (name, meta) in enumerate(axis_meta.items()):
                table.setItem(row, 0, QTableWidgetItem(name))
                table.setItem(row, 1, QTableWidgetItem(meta["role"]))
                table.setItem(row, 2, QTableWidgetItem(meta.get("unit") or ""))
                table.setItem(row, 3, QTableWidgetItem(meta.get("label") or ""))

        context.artifact_selected.connect(show_artifact)
        return container


def _describe(artifact: Artifact) -> str:
    lines = [f"<b>{artifact.label}</b>"]
    if artifact.produced_by:
        lines.append(f"Produced by: {artifact.produced_by} ({artifact.output_port})")
    else:
        lines.append("Raw data")
    dims = ", ".join(artifact.dataset.dims) or "-"
    lines.append(f"Dimensions: {dims}")
    return "<br>".join(lines)
