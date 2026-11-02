"""1D spectrum view: intensity vs. a single spectral-like axis.

Matches any artifact whose dataset is one-dimensional, has an axis
tagged :data:`AxisRole.SPECTRAL` (e.g. Raman shift, wavelength,
retention time - any "x axis you scan over") and a data variable tagged
:data:`AxisRole.INTENSITY`. Nothing about Raman specifically is assumed:
the axis label/unit shown on the plot come entirely from the dataset's
:class:`~alchemetra.data.dataset.AxisMeta`.
"""

from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtWidgets import QWidget

from ...data.artifact import Artifact
from ...data.dataset import AxisRole
from ...plugins.registry import register_plugin
from ..context import UiContext
from ..views.base import ViewPlugin


@register_plugin
class SpectrumView(ViewPlugin):
    """Line plot of intensity against a single spectral-like axis."""

    plugin_id = "core.view.spectrum"
    display_name = "Spectrum"
    description = "1D line plot of intensity vs. a spectral-like axis."
    priority = 10

    @classmethod
    def supports(cls, artifact: Artifact) -> bool:
        dataset = artifact.dataset
        if len(dataset.dims) != 1:
            return False
        return bool(
            dataset.axes_with_role(AxisRole.SPECTRAL)
            and dataset.axes_with_role(AxisRole.INTENSITY)
        )

    def create_widget(self, artifact: Artifact, context: UiContext) -> QWidget:
        dataset = artifact.dataset
        x_axis = dataset.primary_axis(AxisRole.SPECTRAL)
        y_var = dataset.primary_axis(AxisRole.INTENSITY)

        plot_widget = pg.PlotWidget(title=artifact.label)
        plot_widget.showGrid(x=True, y=True, alpha=0.3)

        x_meta = dataset.get_axis_meta(x_axis)
        y_meta = dataset.get_axis_meta(y_var)
        plot_widget.setLabel("bottom", x_meta.label or x_axis, units=x_meta.unit)
        plot_widget.setLabel("left", y_meta.label or y_var, units=y_meta.unit)

        x_values = dataset.xr[x_axis].values
        y_values = dataset.xr[y_var].values
        plot_widget.plot(x_values, y_values, pen=pg.mkPen(width=2))

        return plot_widget
