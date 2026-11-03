"""Project save/load round-trip (arrays, axis roles, annotations, provenance)."""
import numpy as np
import xarray as xr

from alchemetra.annotations.peak import PeakAnnotation
from alchemetra.annotations.roi import ROIAnnotation
from alchemetra.annotations.separator import SeparatorAnnotation
from alchemetra.builtin import register_all
from alchemetra.data.artifact import Artifact
from alchemetra.data.dataset import AxisRole, Dataset
from alchemetra.project.project import Project
from alchemetra.project.project_manager import ProjectManager
from alchemetra.workflow.graph import NodeInstance

register_all()


def _artifact() -> Artifact:
    xr_ds = xr.Dataset(
        {"intensity": ("wavenumber", np.array([1.0, 2.0, 3.0, 4.0]))},
        coords={"wavenumber": np.array([100.0, 200.0, 300.0, 400.0])},
    )
    ds = Dataset(xr_ds)
    ds.set_axis_role("wavenumber", AxisRole.SPECTRAL, unit="cm^-1", label="Raman shift")
    ds.set_axis_role("intensity", AxisRole.INTENSITY, unit="counts")
    return Artifact(dataset=ds).labelled("raw spectrum")


def _project() -> Project:
    project = Project(name="demo")
    raw = _artifact()
    project.add_raw_data("source", raw)
    project.workflow.add_node(NodeInstance(id="scale", plugin_id="core.example.scale",
                                           params={"factor": 2.0}))
    project.workflow.connect("source", "out", "scale", "in")
    project.run()
    project.add_annotation(PeakAnnotation(artifact_id=raw.id, position=250.0, width=20.0))
    project.add_annotation(ROIAnnotation(artifact_id=raw.id,
                                         bounds={"SPECTRAL": (100.0, 300.0)}))
    project.add_annotation(SeparatorAnnotation(artifact_id=raw.id, position=1.5,
                                               axis_role=AxisRole.TEMPORAL))
    return project


def test_roundtrip_restores_arrays_roles_and_labels(tmp_path):
    project = _project()
    ProjectManager.save(project, tmp_path / "p")
    loaded = ProjectManager.load(tmp_path / "p")

    assert loaded.name == "demo"
    raw = loaded.raw_data["source"]
    np.testing.assert_allclose(raw.dataset.xr["intensity"].values, [1, 2, 3, 4])
    assert raw.dataset.primary_axis(AxisRole.SPECTRAL) == "wavenumber"
    assert raw.dataset.get_axis_meta("wavenumber").unit == "cm^-1"
    assert raw.label == "raw spectrum"

    scaled = next(a for a in loaded.derived_data.values() if a.produced_by == "scale")
    np.testing.assert_allclose(scaled.dataset.xr["intensity"].values, [2, 4, 6, 8])


def test_roundtrip_restores_annotations_and_provenance(tmp_path):
    project = _project()
    ProjectManager.save(project, tmp_path / "p")
    loaded = ProjectManager.load(tmp_path / "p")

    kinds = sorted(type(a).__name__ for a in loaded.annotations)
    assert kinds == ["PeakAnnotation", "ROIAnnotation", "SeparatorAnnotation"]
    sep = next(a for a in loaded.annotations if isinstance(a, SeparatorAnnotation))
    assert sep.axis_role is AxisRole.TEMPORAL
    peak = next(a for a in loaded.annotations if isinstance(a, PeakAnnotation))
    assert peak.position == 250.0

    scaled = next(a for a in loaded.derived_data.values() if a.produced_by == "scale")
    lineage = loaded.provenance.lineage_of(scaled.id)
    assert [r.node_id for r in lineage] == ["scale"]


def test_loaded_project_can_run_again(tmp_path):
    ProjectManager.save(_project(), tmp_path / "p")
    loaded = ProjectManager.load(tmp_path / "p")
    result = loaded.run()
    out_id = result.node_outputs["scale"]["out"]
    np.testing.assert_allclose(result.artifacts[out_id].dataset.xr["intensity"].values,
                               [2, 4, 6, 8])


def test_repeated_project_run_uses_cache():
    project = _project()
    assert project.run().executed_nodes == []   # already computed in _project()
