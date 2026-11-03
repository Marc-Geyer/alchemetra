"""Default table view plugin.

Renders any artifact whose dataset is a flat rows-by-columns table as a
``QTableWidget``. This is the view used for the default CSV import plugin:
a header-driven CSV becomes a dataset with one dimension (the observations,
``"index"``) and one data variable per column, which is displayed as a
two-dimensional table.
"""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QWidget, QVBoxLayout

from ...data.artifact import Artifact
from ...data.dataset import AxisRole
from ...plugins.base import PluginKind
from ...plugins.registry import register_plugin
from ..context import UiContext
from ..views.base import ViewPlugin


@register_plugin
class TableView(ViewPlugin):
    """Display tabular datasets as an interactive table."""

    plugin_id: ClassVar[str] = "core.view.table"
    display_name: ClassVar[str] = "Table"
    description: ClassVar[str] = "Tabular display of artifact data (rows x columns)."
    version: ClassVar[str] = "0.1.0"
    plugin_kind: ClassVar[PluginKind] = PluginKind.VISUALIZATION
    priority: ClassVar[int] = 10

    #: Axis roles that mark a dataset as a *signal* array (1D spectra,
    #: 2D heatmaps, ...). Such artifacts are visualised by the dedicated
    #: spectrum/heatmap views instead of the generic table.
    _SIGNAL_AXIS_ROLES: ClassVar[frozenset[AxisRole]] = frozenset(
        {
            AxisRole.SPECTRAL,
            AxisRole.TEMPORAL,
            AxisRole.SPATIAL,
            AxisRole.POTENTIAL,
            AxisRole.CURRENT,
        }
    )

    @classmethod
    def supports(cls, artifact: Artifact) -> bool:
        dataset = artifact.dataset
        dims = list(dataset.dims)
        if not dims:
            return False
        for name in dims:
            if dataset.get_axis_meta(name).role in cls._SIGNAL_AXIS_ROLES:
                return False

        data_vars = list(dataset.xr.data_vars)
        if len(data_vars) > 1:
            # A genuine rows-by-columns table: one variable per column.
            return True
        if len(data_vars) == 1:
            # Single-column datasets are tables as long as the value axis
            # is tagged as intensity-like; bare untagged arrays are left to
            # other (or no) view.
            return dataset.get_axis_meta(data_vars[0]).role == AxisRole.INTENSITY

        return False

    def create_widget(self, artifact: Artifact, context: UiContext) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        table = QTableWidget()
        layout.addWidget(table)

        self._populate(artifact, table)
        return container

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------
    def _populate(self, artifact: Artifact, table: QTableWidget) -> None:
        dataset = artifact.dataset
        data_vars = list(dataset.xr.data_vars)

        if not data_vars or len(dataset.dims) != 1:
            table.clearContents()
            table.setRowCount(0)
            table.setColumnCount(0)
            return

        dim: str = list(dataset.dims)[0]
        n_rows = int(dataset.xr.sizes[dim])

        table.setColumnCount(len(data_vars))
        table.setRowCount(n_rows)
        table.setHorizontalHeaderLabels(list(data_vars))

        columns = [dataset.xr[name].values for name in data_vars]
        header_labels = (
            [str(v) for v in dataset.xr[dim].values]
            if dim in dataset.xr.coords
            else [str(i) for i in range(n_rows)]
        )

        for row in range(n_rows):
            for col_idx, values in enumerate(columns):
                table.setItem(row, col_idx, QTableWidgetItem(_format_value(values[row])))

        table.setVerticalHeaderLabels(header_labels)


def _format_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
