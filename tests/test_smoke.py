"""End-to-end smoke test for the Alchemetra core.

Builds a tiny spectral dataset, wires up a one-node workflow using the
``core.example.scale`` plugin, round-trips it through a processing
template, executes it, and checks the result plus provenance.
"""

from __future__ import annotations

import numpy as np
import xarray as xr

# Importing this registers the example node with the plugin registry.
from alchemetra.builtin import example_nodes  # noqa: F401
from alchemetra.data.artifact import Artifact
from alchemetra.data.dataset import AxisRole, Dataset
from alchemetra.workflow.execution import ExecutionEngine
from alchemetra.workflow.graph import NodeInstance, WorkflowGraph


def _make_source_artifact() -> Artifact:
    wavenumber = np.array([100.0, 200.0, 300.0, 400.0])
    intensity = np.array([1.0, 2.0, 3.0, 4.0])

    xr_dataset = xr.Dataset(
        {"intensity": ("wavenumber", intensity)},
        coords={"wavenumber": wavenumber},
    )

    dataset = Dataset(xr_dataset)
    dataset.set_axis_role(
        "wavenumber", AxisRole.SPECTRAL, unit="cm^-1", label="Raman shift"
    )
    dataset.set_axis_role("intensity", AxisRole.INTENSITY, unit="counts")

    return Artifact(dataset=dataset).labelled("raw spectrum")


def test_scale_node_via_template_roundtrip():
    source = _make_source_artifact()

    graph = WorkflowGraph()
    graph.add_node(NodeInstance(id="source", plugin_id="core.example.source"))
    graph.add_node(
        NodeInstance(
            id="scale",
            plugin_id="core.example.scale",
            params={"factor": 2.0},
        )
    )
    graph.connect("source", "out", "scale", "in")

    # Round-trip through a processing template.
    template = graph.to_template()
    reloaded = WorkflowGraph.from_template(template)

    engine = ExecutionEngine(reloaded)
    result = engine.run(source_artifacts={"source": source})

    scale_output_id = result.node_outputs["scale"]["out"]
    scaled_artifact = result.artifacts[scale_output_id]

    np.testing.assert_allclose(
        scaled_artifact.dataset.xr["intensity"].values, [2.0, 4.0, 6.0, 8.0]
    )

    # Axis-role metadata survives the processing step (data layer owns
    # axis semantics, not the node).
    assert scaled_artifact.dataset.primary_axis(AxisRole.SPECTRAL) == "wavenumber"
    assert scaled_artifact.dataset.primary_axis(AxisRole.INTENSITY) == "intensity"

    # Provenance: the scaled artifact's lineage includes the scale node
    # and traces back to the source artifact.
    lineage = engine.tracker.lineage_of(scaled_artifact.id)
    assert len(lineage) == 1
    record = lineage[0]
    assert record.node_id == "scale"
    assert record.plugin_id == "core.example.scale"
    assert record.params["factor"] == 2.0
    assert record.inputs["in"] == source.id
    assert record.outputs["out"] == scaled_artifact.id

    # Re-running with the same inputs/params is served from cache (no
    # extra execution recorded for "scale").
    result2 = engine.run(source_artifacts={"source": source})
    assert result2.executed_nodes == []
    assert result2.node_outputs["scale"]["out"] == scale_output_id
