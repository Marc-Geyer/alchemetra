"""UI shell smoke tests (headless via the Qt offscreen platform)."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import xarray as xr
import pytest

from alchemetra.data.artifact import Artifact
from alchemetra.data.dataset import AxisRole, Dataset
from alchemetra.plugins.base import PluginKind
from alchemetra.plugins.registry import PluginRegistry
from alchemetra.project.project import Project
from alchemetra.ui.context import UiContext
from alchemetra.ui.main_window import MainWindow


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    return instance


def _spectrum_artifact() -> Artifact:
    xr_ds = xr.Dataset(
        {"intensity": ("wavenumber", np.array([1.0, 2.0, 3.0]))},
        coords={"wavenumber": np.array([100.0, 200.0, 300.0])},
    )
    ds = Dataset(xr_ds)
    ds.set_axis_role("wavenumber", AxisRole.SPECTRAL, unit="cm^-1")
    ds.set_axis_role("intensity",  AxisRole.INTENSITY, unit="counts")
    return Artifact(dataset=ds).labelled("spectrum")


def _heatmap_artifact() -> Artifact:
    intensity = np.arange(12, dtype=float).reshape(3, 4)
    xr_ds = xr.Dataset(
        {"intensity": (("wavenumber", "time"), intensity)},
        coords={"wavenumber": np.array([100.0, 200.0, 300.0]),
                "time":       np.array([0.0, 1.0, 2.0, 3.0])},
    )
    ds = Dataset(xr_ds)
    ds.set_axis_role("wavenumber", AxisRole.SPECTRAL,  unit="cm^-1")
    ds.set_axis_role("time",       AxisRole.TEMPORAL,  unit="s")
    ds.set_axis_role("intensity",  AxisRole.INTENSITY, unit="counts")
    return Artifact(dataset=ds).labelled("heatmap")


def test_builtin_panels_registered(app):
    """MainWindow startup registers all built-in panels."""
    MainWindow(UiContext(Project()))
    panel_ids = {p.plugin_id for p in PluginRegistry.all(PluginKind.PANEL)}
    assert "core.panel.project_explorer" in panel_ids
    assert "core.panel.properties"       in panel_ids
    assert "core.panel.workflow"         in panel_ids


def test_open_views(app):
    """Opening views for spectrum and heatmap artifacts creates tabs."""
    project  = Project()
    spectrum = _spectrum_artifact()
    heatmap  = _heatmap_artifact()
    project.raw_data["s1"] = spectrum
    project.raw_data["h1"] = heatmap
    project.derived_data[spectrum.id] = spectrum
    project.derived_data[heatmap.id]  = heatmap

    window = MainWindow(UiContext(project))
    window.open_view_for_artifact(spectrum.id)
    window.open_view_for_artifact(heatmap.id)

    assert len(window._open_views) == 2
    assert window._tabs.count()    == 2


def test_duplicate_view_focuses_existing_tab(app):
    """Re-requesting an open view focuses its tab instead of opening another."""
    project  = Project()
    spectrum = _spectrum_artifact()
    project.raw_data["s1"] = spectrum
    project.derived_data[spectrum.id] = spectrum

    window = MainWindow(UiContext(project))
    window.open_view_for_artifact(spectrum.id)
    window.open_view_for_artifact(spectrum.id)   # second time

    assert window._tabs.count() == 1


def test_no_view_for_untagged_artifact(app):
    """Artifacts without recognised axis roles have no matching view plugin."""
    xr_ds    = xr.Dataset({"value": ("idx", np.array([1, 2, 3]))})
    artifact = Artifact(dataset=Dataset(xr_ds)).labelled("untagged")
    assert MainWindow._best_view_for(artifact) is None


def test_import_save_open_and_template_via_window(app, tmp_path):
    """End-to-end through the window's path-based actions (no dialogs)."""
    csv = tmp_path / "raman.csv"
    csv.write_text("100,1\n200,2\n300,3\n")

    window = MainWindow(UiContext(Project()))
    window.import_file(csv)
    assert "raman" in window.context.project.raw_data
    assert window._tabs.count() == 1            # a view opened automatically

    # raw artifacts are selectable/viewable before any workflow run
    raw = window.context.project.raw_data["raman"]
    assert window.context.artifact(raw.id) is raw

    window.save_project(tmp_path / "proj")
    window.export_template(tmp_path / "wf.json")

    other = MainWindow(UiContext(Project()))
    other.open_project(tmp_path / "proj")
    assert "raman" in other.context.project.raw_data
    other.load_template(tmp_path / "wf.json")
    assert "raman" in other.context.project.workflow.nodes
