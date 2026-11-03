"""Core layer: workflow graph validation and execution engine edge cases."""

from __future__ import annotations

import pytest

from alchemetra.builtin import register_all  # noqa: F401 – registers built-ins
from alchemetra.data.artifact import Artifact
from alchemetra.data.dataset import AxisRole, Dataset
from alchemetra.workflow.execution import ExecutionEngine
from alchemetra.workflow.graph import GraphError, NodeInstance, WorkflowGraph


def _source_artifact() -> Artifact:
    import numpy as np
    import xarray as xr

    xr_ds = xr.Dataset(
        {"intensity": ("wavenumber", np.array([1.0, 2.0, 3.0]))},
        coords={"wavenumber": np.array([100.0, 200.0, 300.0])},
    )
    ds = Dataset(xr_ds)
    ds.set_axis_role("wavenumber", AxisRole.SPECTRAL, unit="cm^-1")
    ds.set_axis_role("intensity", AxisRole.INTENSITY, unit="counts")
    return Artifact(dataset=ds).labelled("raw spectrum")


def test_cycle_detection() -> None:
    graph = WorkflowGraph()
    graph.add_node(NodeInstance(id="a", plugin_id="x"))
    graph.add_node(NodeInstance(id="b", plugin_id="x"))
    graph.connect("a", "out", "b", "in")
    with pytest.raises(GraphError):
        graph.connect("b", "out", "a", "in")


def test_execution_requires_source_artifact_for_entry_node() -> None:
    graph = WorkflowGraph()
    graph.add_node(NodeInstance(id="source", plugin_id="core.source.csv"))
    graph.add_node(NodeInstance(id="scale", plugin_id="core.example.scale", params={"factor": 2.0}))
    graph.connect("source", "out", "scale", "in")

    engine = ExecutionEngine(graph)
    with pytest.raises(GraphError):
        engine.run(source_artifacts={})
