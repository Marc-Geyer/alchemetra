"""Project-level workflow editing: add / remove / parameter changes."""
import numpy as np
import pytest
import xarray as xr

from alchemetra.builtin import register_all
from alchemetra.data.artifact import Artifact
from alchemetra.data.dataset import AxisRole, Dataset
from alchemetra.project.project import Project

register_all()


def _project():
    ds = Dataset(xr.Dataset({"intensity": ("wavenumber", np.array([1., 2., 3., 4.]))},
                            coords={"wavenumber": [100., 200., 300., 400.]}))
    ds.set_axis_role("wavenumber", AxisRole.SPECTRAL)
    ds.set_axis_role("intensity", AxisRole.INTENSITY)
    project = Project()
    project.add_raw_data("src", Artifact(dataset=ds).labelled("raw"))
    scale = project.add_processing_node("core.example.scale", after="src", params={"factor": 2.0})
    norm = project.add_processing_node("core.node.normalize", after=scale.id)
    return project, scale, norm


def _out(project, result, node_id):
    return result.artifacts[result.node_outputs[node_id]["out"]]


def test_chain_is_connected_and_runs():
    project, scale, norm = _project()
    assert (scale.id, norm.id) == ("scale", "normalize")
    result = project.run()
    np.testing.assert_allclose(_out(project, result, "normalize").dataset.xr["intensity"].values,
                               [.25, .5, .75, 1.0])


def test_unknown_plugin_leaves_graph_untouched():
    project, *_ = _project()
    before = set(project.workflow.nodes)
    with pytest.raises(KeyError):
        project.add_processing_node("does.not.exist", after="src")
    assert set(project.workflow.nodes) == before


def test_set_params_validates_and_drops_stale_derived():
    project, scale, norm = _project()
    project.run()
    with pytest.raises(ValueError):
        project.set_node_params("normalize", {"mode": "bogus"})
    assert norm.params["mode"] == "max"

    project.set_node_params("scale", {"factor": 4.0})
    assert not any(a.produced_by in {"scale", "normalize"} for a in project.derived_data.values())
    result = project.run()
    assert set(result.executed_nodes) == {"scale", "normalize"}
    np.testing.assert_allclose(_out(project, result, "scale").dataset.xr["intensity"].values,
                               [4, 8, 12, 16])


def test_remove_node_drops_downstream_derived_and_protects_entry():
    project, scale, norm = _project()
    project.run()
    project.remove_node("scale")
    assert "scale" not in project.workflow.nodes and "normalize" in project.workflow.nodes
    assert not any(a.produced_by in {"scale", "normalize"} for a in project.derived_data.values())
    with pytest.raises(ValueError):
        project.remove_node("src")
