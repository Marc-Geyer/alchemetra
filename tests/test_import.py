"""CSV import through DataSourcePlugins."""
import numpy as np
import pytest

from alchemetra.builtin import register_all
from alchemetra.data.dataset import AxisRole
from alchemetra.project.project import Project
from alchemetra.services.import_service import ImportService
from alchemetra.workflow.graph import NodeInstance

register_all()


def test_import_two_column_csv_with_header(tmp_path):
    f = tmp_path / "sample.csv"
    f.write_text("shift,counts\n100,1\n200,2\n300,3\n")
    project = Project()
    (artifact,) = ImportService.import_file(project, f)

    assert "sample" in project.raw_data and "sample" in project.workflow.nodes
    ds = artifact.dataset
    assert ds.primary_axis(AxisRole.SPECTRAL) == "wavenumber"
    np.testing.assert_allclose(ds.xr["intensity"].values, [1, 2, 3])
    assert artifact.label == "sample"


def test_import_multicolumn_gives_heatmap_shape(tmp_path):
    f = tmp_path / "series.txt"
    f.write_text("# comment\n100\t1\t2\t3\n200\t4\t5\t6\n")
    (artifact,) = ImportService.import_file(Project(), f)
    ds = artifact.dataset
    assert set(ds.dims) == {"wavenumber", "time"}
    assert ds.primary_axis(AxisRole.TEMPORAL) == "time"
    assert ds.xr["intensity"].shape == (2, 3)


def test_duplicate_file_names_get_unique_node_ids(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text("1,2\n3,4\n")
    project = Project()
    ImportService.import_file(project, f)
    ImportService.import_file(project, f)
    assert set(project.raw_data) == {"a", "a_2"}


def test_unsupported_extension_and_bad_content(tmp_path):
    bad_ext = tmp_path / "x.xyz"
    bad_ext.write_text("1,2")
    with pytest.raises(ValueError):
        ImportService.import_file(Project(), bad_ext)
    bad = tmp_path / "bad.csv"
    bad.write_text("1,2\n3,abc\n")
    with pytest.raises(ValueError):
        ImportService.import_file(Project(), bad)


def test_imported_data_runs_through_workflow(tmp_path):
    f = tmp_path / "s.csv"
    f.write_text("1,10\n2,20\n")
    project = Project()
    ImportService.import_file(project, f)
    project.workflow.add_node(NodeInstance(id="scale", plugin_id="core.example.scale",
                                           params={"factor": 3.0}))
    project.workflow.connect("s", "out", "scale", "in")
    result = project.run()
    out = result.artifacts[result.node_outputs["scale"]["out"]]
    np.testing.assert_allclose(out.dataset.xr["intensity"].values, [30, 60])
