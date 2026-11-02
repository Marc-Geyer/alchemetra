"""Smoke test for the PySide6 UI shell.

Runs with the ``offscreen`` Qt platform plugin so it works in headless
CI/sandbox environments. Exercises: main window construction (panel
discovery/creation), and opening views for artifacts via
:class:`alchemetra.ui.context.UiContext`.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import xarray as xr
from PySide6.QtWidgets import QApplication

from alchemetra.data.artifact import Artifact
from alchemetra.data.dataset import AxisRole, Dataset
from alchemetra.plugins.base import PluginKind
from alchemetra.plugins.registry import PluginRegistry
from alchemetra.project.project import Project
from alchemetra.ui.context import UiContext
from alchemetra.ui.main_window import MainWindow


def _spectrum_artifact() -> Artifact:
    wavenumber = np.array([100.0, 200.0, 300.0, 400.0])
    intensity = np.array([1.0, 2.0, 3.0, 4.0])
    xr_dataset = xr.Dataset(
        {"intensity": ("wavenumber", intensity)},
        coords={"wavenumber": wavenumber},
    )
    dataset = Dataset(xr_dataset)
    dataset.set_axis_role("wavenumber", AxisRole.SPECTRAL, unit="cm^-1")
    dataset.set_axis_role("intensity", AxisRole.INTENSITY, unit="counts")
    return Artifact(dataset=dataset).labelled("raw spectrum")


def _heatmap_artifact() -> Artifact:
    wavenumber = np.array([100.0, 200.0, 300.0])
    time = np.array([0.0, 1.0, 2.0, 3.0])
    intensity = np.arange(12, dtype=float).reshape(3, 4)
    xr_dataset = xr.Dataset(
        {"intensity": (("wavenumber", "time"), intensity)},
        coords={"wavenumber": wavenumber, "time": time},
    )
    dataset = Dataset(xr_dataset)
    dataset.set_axis_role("wavenumber", AxisRole.SPECTRAL, unit="cm^-1")
    dataset.set_axis_role("time", AxisRole.TEMPORAL, unit="s")
    dataset.set_axis_role("intensity", AxisRole.INTENSITY, unit="counts")
    return Artifact(dataset=dataset).labelled("raw heatmap")


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_creates_builtin_panels():
    _app()
    project = Project()
    window = MainWindow(UiContext(project))

    panel_ids = {plugin_cls.plugin_id for plugin_cls in PluginRegistry.all(PluginKind.PANEL)}
    assert "core.panel.project_explorer" in panel_ids
    assert "core.panel.properties" in panel_ids
    assert "core.panel.workflow" in panel_ids
    assert set(window._docks.keys()) == panel_ids


def test_open_views_for_spectrum_and_heatmap_artifacts():
    _app()
    project = Project()
    spectrum = _spectrum_artifact()
    heatmap = _heatmap_artifact()
    project.raw_data["spectrum_source"] = spectrum
    project.raw_data["heatmap_source"] = heatmap
    project.derived_data[spectrum.id] = spectrum
    project.derived_data[heatmap.id] = heatmap

    window = MainWindow(UiContext(project))

    window.open_view_for_artifact(spectrum.id)
    window.open_view_for_artifact(heatmap.id)

    assert len(window._open_views) == 2
    assert window._tabs.count() == 2

    # Re-requesting an already-open view focuses it rather than opening
    # a second tab.
    window.open_view_for_artifact(spectrum.id)
    assert window._tabs.count() == 2


def test_no_view_for_unmatched_artifact():
    _app()
    project = Project()

    # A dataset with no recognised axis roles at all.
    xr_dataset = xr.Dataset({"value": ("index", np.array([1, 2, 3]))})
    dataset = Dataset(xr_dataset)
    artifact = Artifact(dataset=dataset).labelled("untagged data")

    project.raw_data["source"] = artifact
    project.derived_data[artifact.id] = artifact

    window = MainWindow(UiContext(project))
    assert window._best_view_for(artifact) is None
