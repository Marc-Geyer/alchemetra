"""Example processing-node plugins.

These exist to (a) give the execution engine and UI something to run
out of the box and (b) serve as minimal, readable reference
implementations for third-party plugin authors. They deliberately stay
domain-agnostic: :class:`ScaleNode` works on any dataset that has a data
variable named ``"intensity"``, regardless of which axis roles (Raman
wavenumber, chromatography retention time, ...) are attached to it.
"""

from __future__ import annotations

from typing import Any

from ..data.artifact import Artifact
from ..plugins.registry import register_plugin
from ..workflow.node import NodeBase, ParameterSpec, PortSpec


@register_plugin
class ScaleNode(NodeBase):
    """Multiply the ``intensity`` variable of the input dataset by a
    constant factor.

    This is the simplest possible processing node: one input port, one
    output port, one numeric parameter. It demonstrates the expected
    pattern for real nodes:

    * use :meth:`~alchemetra.data.dataset.Dataset.copy_with` to derive a
      new :class:`~alchemetra.data.dataset.Dataset` (this carries over
      axis-role metadata automatically for unchanged dimensions/
      coordinates/variables);
    * wrap the result in a fresh :class:`Artifact` and give it a
      readable label via :meth:`Artifact.labelled`;
    * never mutate the input artifact's dataset in place.
    """

    plugin_id = "core.example.scale"
    display_name = "Scale"
    description = "Multiply the 'intensity' data variable by a constant factor."

    input_ports = (
        PortSpec(name="in", label="Input"),
    )
    output_ports = (
        PortSpec(name="out", label="Output"),
    )
    parameters = (
        ParameterSpec(
            name="factor",
            kind="float",
            default=1.0,
            label="Scale factor",
        ),
    )

    def run(
        self, inputs: dict[str, Artifact], params: dict[str, Any]
    ) -> dict[str, Artifact]:
        artifact = inputs["in"]
        factor = params["factor"]

        scaled_xr = artifact.dataset.xr.copy()
        scaled_xr["intensity"] = scaled_xr["intensity"] * factor

        new_dataset = artifact.dataset.copy_with(scaled_xr)
        new_artifact = Artifact(dataset=new_dataset).labelled(
            f"{artifact.label} (x{factor:g})"
        )
        return {"out": new_artifact}
