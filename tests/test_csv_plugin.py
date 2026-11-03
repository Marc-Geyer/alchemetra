"""Tests for the default CSV plugin (data source + table view) and the
project save/reopen round-trip.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
import xarray as xr

# Importing the built-in submodules runs their ``@register_plugin``
# decorators, just like the application's plugin discovery does.
import alchemetra.builtin.csv_source  # noqa: F401
from alchemetra.data.artifact import Artifact
from alchemetra.data.dataset import AxisRole, Dataset
from alchemetra.plugins.registry import PluginKind, PluginRegistry
from alchemetra.project.project import Project
from alchemetra.project.project_manager import ProjectManager
from alchemetra.ui.builtin import table_view as table_view_module  # noqa: F401
from alchemetra.ui.builtin.table_view import TableView
from alchemetra.workflow.execution import ExecutionEngine
from alchemetra.workflow.graph import NodeInstance, WorkflowGraph


CSV_CONTENT = """channel_1,channel_2,channel_3
0.12,0.34,0.56
0.45,0.78,1.12
0.98,1.43,2.01
"""


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    path = tmp_path / "measurements.csv"
    path.write_text(CSV_CONTENT, encoding="utf-8")
    return path


def test_csv_source_loads_table_artifact(csv_path: Path) -> None:
    plugin_cls = PluginRegistry.get(PluginKind.DATA_SOURCE, "core.source.csv")
    artifacts = plugin_cls().load(csv_path)

    assert set(artifacts) == {"out"}
    artifact = artifacts["out"]

    assert artifact.label == "measurements"
    assert artifact.produced_by is None
    assert artifact.output_port == "out"

    assert artifact.dataset.dims == ("index",)
    assert list(artifact.dataset.xr.data_vars) == [
        "channel_1",
        "channel_2",
        "channel_3",
    ]
    np.testing.assert_allclose(
        artifact.dataset.xr["channel_1"].values, [0.12, 0.45, 0.98]
    )
    np.testing.assert_allclose(
        artifact.dataset.xr["channel_3"].values, [0.56, 1.12, 2.01]
    )

    # Row axis is untyped, each channel is an intensity-like variable.
    assert artifact.dataset.get_axis_meta("index").role is AxisRole.GENERIC
    assert artifact.dataset.axes_with_role(AxisRole.INTENSITY) == [
        "channel_1",
        "channel_2",
        "channel_3",
    ]


def test_csv_source_load_requires_header_and_data(csv_path: Path) -> None:
    plugin_cls = PluginRegistry.get(PluginKind.DATA_SOURCE, "core.source.csv")

    csv_path.write_text("only_one_column\n", encoding="utf-8")
    with pytest.raises(ValueError, match="needs a header and data rows"):
        plugin_cls().load(csv_path)


def test_csv_source_as_workflow_entry_point(csv_path: Path) -> None:
    plugin_cls = PluginRegistry.get(PluginKind.DATA_SOURCE, "core.source.csv")
    artifact = plugin_cls().load(csv_path)["out"]

    graph = WorkflowGraph()
    graph.add_node(NodeInstance(id="source", plugin_id="core.source.csv"))

    engine = ExecutionEngine(graph)
    result = engine.run(source_artifacts={"source": artifact})

    # The source node is an entry point: no registry lookup, no execution.
    assert result.executed_nodes == []
    assert result.node_outputs["source"]["out"] == artifact.id
    assert result.artifacts[artifact.id] is artifact


def test_project_save_and_reload_roundtrip(tmp_path: Path) -> None:
    plugin_cls = PluginRegistry.get(PluginKind.DATA_SOURCE, "core.source.csv")
    artifact = plugin_cls().load("samples/multichannel.csv")["out"]

    project = Project(name="Roundtrip")
    project.raw_data["source"] = artifact

    project_dir = tmp_path / "project"
    ProjectManager.save(project, project_dir)
    loaded = ProjectManager.load(project_dir)

    assert loaded.name == "Roundtrip"
    assert "source" in loaded.raw_data
    loaded_artifact = loaded.raw_data["source"]

    assert loaded_artifact.id == artifact.id
    assert loaded_artifact.label == artifact.label
    assert loaded_artifact.produced_by is None
    assert loaded_artifact.output_port == "out"

    np.testing.assert_allclose(
        loaded_artifact.dataset.xr["channel_2"].values,
        artifact.dataset.xr["channel_2"].values,
    )
    assert loaded_artifact.dataset.axis_meta_dict() == artifact.dataset.axis_meta_dict()


def test_table_view_renders_csv_artifact() -> None:
    from PySide6.QtWidgets import QApplication, QTableWidget

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    plugin_cls = PluginRegistry.get(PluginKind.DATA_SOURCE, "core.source.csv")
    artifact = plugin_cls().load("samples/multichannel.csv")["out"]

    view = TableView()
    assert view.supports(artifact)

    widget = view.create_widget(artifact, None)
    tables = widget.findChildren(QTableWidget)
    assert len(tables) == 1
    table = tables[0]

    assert table.rowCount() == 8
    assert table.columnCount() == 3
    assert [
        table.horizontalHeaderItem(i).text() for i in range(table.columnCount())
    ] == ["channel_1", "channel_2", "channel_3"]
    assert table.item(0, 0).text() == "0.12"
    assert table.item(2, 2).text() == "2.01"


def test_artifact_is_rejected_by_table_view_when_not_tabular() -> None:
    xr_dataset = xr.Dataset({"value": ("index", np.array([1.0, 2.0, 3.0]))})
    dataset = Dataset(xr_dataset)
    artifact = Artifact(dataset=dataset).labelled("untagged data")

    assert TableView().supports(artifact) is False
