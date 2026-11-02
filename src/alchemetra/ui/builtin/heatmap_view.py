"""Time-spectra heatmap view: intensity over a spectral axis and a
temporal axis.

This generalises the original Raman time-spectra heatmap proof of
concept: it matches any two-dimensional artifact with one axis tagged
:data:`AxisRole.SPECTRAL`, one tagged :data:`AxisRole.TEMPORAL`, and an
:data:`AxisRole.INTENSITY` variable - so the same widget works for
e.g. chromatography-vs-time data without any code change, as long as the
data layer tags the axes correctly.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget

from ...data.artifact import Artifact
from ...data.dataset import AxisRole
from ...plugins.registry import register_plugin
from ..context import UiContext
from ..views.base import ViewPlugin

# Use numpy/row-major (rows = y axis, columns = x axis) image
# orientation throughout this module - matches how the (spectral,
# temporal) array is built in create_widget.
pg.setConfigOptions(imageAxisOrder="row-major")


@register_plugin
class HeatmapView(ViewPlugin):
    """2D heatmap of intensity vs. (spectral axis, temporal axis)."""

    plugin_id = "core.view.heatmap"
    display_name = "Time-Spectra Heatmap"
    description = "2D heatmap of intensity over a spectral axis and a temporal axis."
    priority = 10

    @classmethod
    def supports(cls, artifact: Artifact) -> bool:
        dataset = artifact.dataset
        if len(dataset.dims) != 2:
            return False
        return bool(
            dataset.axes_with_role(AxisRole.SPECTRAL)
            and dataset.axes_with_role(AxisRole.TEMPORAL)
            and dataset.axes_with_role(AxisRole.INTENSITY)
        )

    def create_widget(self, artifact: Artifact, context: UiContext) -> QWidget:
        dataset = artifact.dataset
        spectral_axis = dataset.primary_axis(AxisRole.SPECTRAL)
        temporal_axis = dataset.primary_axis(AxisRole.TEMPORAL)
        intensity_var = dataset.primary_axis(AxisRole.INTENSITY)

        data_array = dataset.xr[intensity_var].transpose(spectral_axis, temporal_axis)
        image = np.asarray(data_array.values)

        spectral_values = np.asarray(dataset.xr[spectral_axis].values)
        temporal_values = np.asarray(dataset.xr[temporal_axis].values)

        plot_item = pg.PlotItem()
        image_view = pg.ImageView(view=plot_item)
        image_view.ui.roiBtn.hide()
        image_view.ui.menuBtn.hide()

        spectral_meta = dataset.get_axis_meta(spectral_axis)
        temporal_meta = dataset.get_axis_meta(temporal_axis)
        plot_item.setLabel(
            "bottom", temporal_meta.label or temporal_axis, units=temporal_meta.unit
        )
        plot_item.setLabel(
            "left", spectral_meta.label or spectral_axis, units=spectral_meta.unit
        )

        x0, dx = _axis_origin_and_step(temporal_values)
        y0, dy = _axis_origin_and_step(spectral_values)

        image_view.setImage(image, pos=[x0, y0], scale=[dx, dy], autoLevels=True)
        return image_view


def _axis_origin_and_step(values: np.ndarray) -> tuple[float, float]:
    """Return ``(origin, step)`` for mapping array indices along an axis
    to coordinate values, assuming roughly uniform spacing."""

    if len(values) == 0:
        return 0.0, 1.0
    if len(values) == 1:
        return float(values[0]), 1.0
    return float(values[0]), float(values[1] - values[0])
