"""Built-in processing nodes. All of them locate axes by *role*, never by name."""
from __future__ import annotations

from typing import Any

import xarray as xr
from scipy.signal import savgol_filter

from ..data.artifact import Artifact
from ..data.dataset import AxisRole, Dataset
from ..plugins.registry import register_plugin
from ..workflow.node import NodeBase, ParameterSpec, PortSpec


def _intensity_var(dataset: Dataset) -> str:
    name = dataset.primary_axis(AxisRole.INTENSITY)
    if name is None:
        raise ValueError("Dataset has no variable tagged with role INTENSITY")
    return name


@register_plugin
class CropNode(NodeBase):
    """Keep only the part of the spectral axis between ``start`` and ``stop``."""

    plugin_id = "core.node.crop"
    display_name = "Crop spectral range"
    description = "Keep data between start and stop on the spectral axis."
    input_ports = (PortSpec(name="in", label="Input", required_role=AxisRole.SPECTRAL),)
    output_ports = (PortSpec(name="out", label="Output"),)
    parameters = (
        ParameterSpec(name="start", kind="float", default=0.0, label="Start"),
        ParameterSpec(name="stop", kind="float", default=10000.0, label="Stop"),
    )

    def run(
        self, inputs: dict[str, Artifact], params: dict[str, Any]
    ) -> dict[str, Artifact]:
        artifact = inputs["in"]
        dataset = artifact.dataset
        axis = dataset.primary_axis(AxisRole.SPECTRAL)
        lo, hi = sorted((float(params["start"]), float(params["stop"])))
        values = dataset.xr[axis].values
        descending = values.size > 1 and values[0] > values[-1]
        selected = dataset.xr.sel(
            {axis: slice(hi, lo) if descending else slice(lo, hi)}
        )
        if selected.sizes[axis] == 0:
            raise ValueError(f"Crop range {lo:g}..{hi:g} contains no points on '{axis}'")
        return {
            "out": Artifact(dataset=dataset.copy_with(selected)).labelled(
                f"{artifact.label} (cropped)"
            )
        }


@register_plugin
class NormalizeNode(NodeBase):
    """Normalise every spectrum along the spectral axis."""

    plugin_id = "core.node.normalize"
    display_name = "Normalize"
    description = "Divide each spectrum by its maximum or by its sum."
    input_ports = (PortSpec(name="in", label="Input", required_role=AxisRole.SPECTRAL),)
    output_ports = (PortSpec(name="out", label="Output"),)
    parameters = (
        ParameterSpec(
            name="mode",
            kind="choice",
            default="max",
            label="Reference",
            choices=("max", "sum"),
        ),
    )

    def run(
        self, inputs: dict[str, Artifact], params: dict[str, Any]
    ) -> dict[str, Artifact]:
        artifact = inputs["in"]
        dataset = artifact.dataset
        axis = dataset.primary_axis(AxisRole.SPECTRAL)
        var = _intensity_var(dataset)
        data = dataset.xr[var]
        magnitude = abs(data)
        ref = (
            magnitude.max(dim=axis)
            if params["mode"] == "max"
            else magnitude.sum(dim=axis)
        )
        normalised = data / ref.where(ref != 0, 1.0)
        new_xr = dataset.xr.copy()
        new_xr[var] = normalised.transpose(*data.dims)
        return {
            "out": Artifact(dataset=dataset.copy_with(new_xr)).labelled(
                f"{artifact.label} (normalized)"
            )
        }


@register_plugin
class SmoothNode(NodeBase):
    """Savitzky-Golay smoothing along the spectral axis."""

    plugin_id = "core.node.smooth"
    display_name = "Smooth (Savitzky-Golay)"
    description = "Savitzky-Golay filter along the spectral axis."
    input_ports = (PortSpec(name="in", label="Input", required_role=AxisRole.SPECTRAL),)
    output_ports = (PortSpec(name="out", label="Output"),)
    parameters = (
        ParameterSpec(
            name="window_length",
            kind="int",
            default=11,
            label="Window (odd)",
            min_value=3,
        ),
        ParameterSpec(
            name="polyorder",
            kind="int",
            default=3,
            label="Polynomial order",
            min_value=0,
        ),
    )

    def run(
        self, inputs: dict[str, Artifact], params: dict[str, Any]
    ) -> dict[str, Artifact]:
        artifact = inputs["in"]
        dataset = artifact.dataset
        axis = dataset.primary_axis(AxisRole.SPECTRAL)
        var = _intensity_var(dataset)
        window, order = int(params["window_length"]), int(params["polyorder"])
        data = dataset.xr[var]
        if window % 2 == 0:
            raise ValueError("Window length must be odd")
        if order >= window:
            raise ValueError("Polynomial order must be smaller than the window length")
        if window > data.sizes[axis]:
            raise ValueError(
                f"Window ({window}) is longer than the axis '{axis}' "
                f"({data.sizes[axis]} points)"
            )
        filtered = savgol_filter(data.values, window, order, axis=data.get_axis_num(axis))
        new_xr = dataset.xr.copy()
        new_xr[var] = data.copy(data=filtered)
        return {
            "out": Artifact(dataset=dataset.copy_with(new_xr)).labelled(
                f"{artifact.label} (smoothed)"
            )
        }
