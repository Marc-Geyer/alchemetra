"""Parameter form, workflow widget and node inspector (headless)."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
import xarray as xr
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox

from alchemetra.data.artifact import Artifact
from alchemetra.data.dataset import AxisRole, Dataset
from alchemetra.project.project import Project
from alchemetra.ui.context import UiContext
from alchemetra.ui.main_window import MainWindow
from alchemetra.ui.widgets.parameter_form import ParameterForm
from alchemetra.workflow.node import ParameterSpec


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_parameter_form_builds_editors_and_emits(app):
    specs = (
        ParameterSpec(name="f", kind="float", default=1.5, label="F", min_value=0, max_value=10),
        ParameterSpec(name="n", kind="int", default=3),
        ParameterSpec(name="b", kind="bool", default=True),
        ParameterSpec(name="c", kind="choice", default="x", choices=("x", "y")),
        ParameterSpec(name="s", kind="str", default="hi"),
    )
    form = ParameterForm(specs, {"n": 7})
    assert form.values() == {"f": 1.5, "n": 7, "b": True, "c": "x", "s": "hi"}

    seen = []
    form.values_changed.connect(seen.append)
    form.findChild(QDoubleSpinBox).setValue(2.5)
    assert seen[-1]["f"] == 2.5
    form.findChild(QComboBox).setCurrentIndex(1)
    assert seen[-1]["c"] == "y"


def test_add_edit_run_remove_through_panels(app):
    ds = Dataset(xr.Dataset({"intensity": ("wavenumber", np.array([1., 2., 3.]))},
                            coords={"wavenumber": [1., 2., 3.]}))
    ds.set_axis_role("wavenumber", AxisRole.SPECTRAL)
    ds.set_axis_role("intensity", AxisRole.INTENSITY)
    project = Project()
    project.add_raw_data("src", Artifact(dataset=ds).labelled("raw"))

    window = MainWindow(UiContext(project))
    workflow = window._docks["core.panel.workflow"].widget()
    inspector = window._docks["core.panel.node_inspector"].widget()

    workflow.select("src")
    workflow.add_node("core.example.scale")          # auto-connected after "src"
    assert project.workflow.incoming_edges("scale")
    assert workflow.selected_node_id() == "scale"

    inspector.findChildren(QDoubleSpinBox)[0].setValue(5.0)
    assert project.workflow.nodes["scale"].params["factor"] == 5.0
    assert workflow.selected_node_id() == "scale"     # selection survives the refresh

    workflow.run_workflow()
    scaled = next(a for a in project.derived_data.values() if a.produced_by == "scale")
    np.testing.assert_allclose(scaled.dataset.xr["intensity"].values, [5, 10, 15])

    workflow.remove_selected()
    assert "scale" not in project.workflow.nodes
    assert inspector.findChildren(QDoubleSpinBox) == []
