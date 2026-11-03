"""Built-in processing nodes (role-based, domain-agnostic)."""
import numpy as np
import pytest
import xarray as xr

from alchemetra.builtin import register_all
from alchemetra.builtin.processing_nodes import CropNode, NormalizeNode, SmoothNode
from alchemetra.data.artifact import Artifact
from alchemetra.data.dataset import AxisRole, Dataset

register_all()


def _artifact(x, y, x_name="wavenumber") -> Artifact:
    ds = Dataset(xr.Dataset({"intensity": (x_name, np.asarray(y, float))},
                            coords={x_name: np.asarray(x, float)}))
    ds.set_axis_role(x_name, AxisRole.SPECTRAL, unit="cm^-1")
    ds.set_axis_role("intensity", AxisRole.INTENSITY)
    return Artifact(dataset=ds).labelled("s")


def _run(node_cls, art, **params):
    node = node_cls()
    return node.run({"in": art}, node.validate_params(params))["out"]


def test_crop_ascending_and_descending():
    out = _run(CropNode, _artifact([100, 200, 300, 400], [1, 2, 3, 4]), start=150, stop=350)
    np.testing.assert_allclose(out.dataset.xr["wavenumber"].values, [200, 300])
    out = _run(CropNode, _artifact([400, 300, 200, 100], [4, 3, 2, 1]), start=150, stop=350)
    np.testing.assert_allclose(out.dataset.xr["intensity"].values, [3, 2])
    assert out.dataset.primary_axis(AxisRole.SPECTRAL) == "wavenumber"   # roles survive


def test_crop_empty_range_raises():
    with pytest.raises(ValueError):
        _run(CropNode, _artifact([100, 200], [1, 2]), start=500, stop=600)


def test_crop_works_for_other_axis_names():
    out = _run(CropNode, _artifact([1, 2, 3, 4], [1, 1, 1, 1], x_name="retention_time"),
               start=2, stop=3)
    assert out.dataset.xr.sizes["retention_time"] == 2


def test_normalize_1d_and_2d():
    out = _run(NormalizeNode, _artifact([1, 2, 3], [1, 2, 4]))
    np.testing.assert_allclose(out.dataset.xr["intensity"].values, [0.25, 0.5, 1.0])

    ds = Dataset(xr.Dataset({"intensity": (("wavenumber", "time"),
                                           np.array([[1., 2.], [2., 4.], [4., 8.]]))},
                            coords={"wavenumber": [1., 2., 3.], "time": [0., 1.]}))
    ds.set_axis_role("wavenumber", AxisRole.SPECTRAL)
    ds.set_axis_role("time", AxisRole.TEMPORAL)
    ds.set_axis_role("intensity", AxisRole.INTENSITY)
    out = _run(NormalizeNode, Artifact(dataset=ds))          # per spectrum (per time step)
    np.testing.assert_allclose(out.dataset.xr["intensity"].values,
                               [[.25, .25], [.5, .5], [1, 1]])
    out = _run(NormalizeNode, _artifact([1, 2, 3], [1, 1, 2]), mode="sum")
    np.testing.assert_allclose(out.dataset.xr["intensity"].values, [.25, .25, .5])


def test_smooth_keeps_constant_signal_and_validates():
    art = _artifact(np.arange(21), np.ones(21))
    out = _run(SmoothNode, art, window_length=5, polyorder=2)
    np.testing.assert_allclose(out.dataset.xr["intensity"].values, np.ones(21))
    with pytest.raises(ValueError):
        _run(SmoothNode, art, window_length=4, polyorder=2)
    with pytest.raises(ValueError):
        _run(SmoothNode, art, window_length=5, polyorder=5)
    with pytest.raises(ValueError):
        _run(SmoothNode, art, window_length=31, polyorder=2)


def test_nodes_require_spectral_role():
    untagged = Artifact(dataset=Dataset(xr.Dataset({"v": ("i", np.arange(3.0))})))
    with pytest.raises(ValueError):
        CropNode().validate_inputs({"in": untagged})
