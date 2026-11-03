"""Semantically annotated dataset wrapper.

Design principle (do not violate): *axis semantics live here, not in
processing or visualisation code*. A processing node that needs "the
spectral axis" or "the time axis" asks the :class:`Dataset` for the
dimension that carries that :class:`AxisRole` - it never hardcodes a
dimension name such as ``"wavenumber"``. This is what allows the same
node (e.g. a slice selector) to work for Raman wavenumber, chromatography
retention time, or any future domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

import xarray as xr


class AxisRole(Enum):
    """Semantic role an axis (dimension, coordinate or data variable) can
    play.

    This list is deliberately generic. For roles that don't fit any of
    the predefined ones, use :data:`AxisRole.CUSTOM` together with the
    ``custom_role`` string on :class:`AxisMeta` - this keeps the enum
    itself stable (and therefore safe to use in saved templates) while
    still allowing domain plugins to introduce new semantic axes.
    """

    GENERIC = auto()
    SPECTRAL = auto()      # e.g. wavenumber, wavelength, m/z
    TEMPORAL = auto()       # acquisition time / elapsed time
    SPATIAL = auto()        # retention time, position, depth, ...
    INTENSITY = auto()      # signal magnitude / counts / absorbance
    POTENTIAL = auto()      # electrochemical potential
    CURRENT = auto()        # electrochemical current
    SAMPLE = auto()         # categorical sample / replicate identifier
    CUSTOM = auto()         # domain-specific role, see AxisMeta.custom_role


@dataclass
class AxisMeta:
    """Metadata describing one axis (dimension, coordinate or variable)."""

    name: str
    role: AxisRole = AxisRole.GENERIC
    unit: str | None = None
    label: str | None = None
    custom_role: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role.name,
            "unit": self.unit,
            "label": self.label,
            "custom_role": self.custom_role,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AxisMeta":
        return cls(
            name=data["name"],
            role=AxisRole[data["role"]],
            unit=data.get("unit"),
            label=data.get("label"),
            custom_role=data.get("custom_role"),
        )


class Dataset:
    """A semantically annotated dataset.

    Wraps an :class:`xarray.Dataset` (chosen because it natively supports
    labelled, multi-dimensional arrays with coordinates - a good fit for
    spectra, time series and heatmaps, and can later be backed by dask
    for out-of-core processing of large datasets without changing this
    interface) and attaches an :class:`AxisMeta` to any number of its
    dimensions, coordinates or data variables.

    Role lookups (:meth:`axes_with_role`, :meth:`primary_axis`) are how
    processing nodes and UI widgets stay domain-agnostic: a "slice
    selector" widget asks for ``AxisRole.SPECTRAL`` and gets back whatever
    dimension name this particular dataset uses for it.
    """

    def __init__(
        self,
        data: xr.Dataset,
        axis_meta: dict[str, AxisMeta] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._data = data
        self._axis_meta: dict[str, AxisMeta] = dict(axis_meta or {})
        #: Free-form bag for instrument metadata, file origin, acquisition
        #: settings, etc. Not interpreted by the core.
        self.metadata: dict[str, Any] = dict(metadata or {})

    # ------------------------------------------------------------------
    # Access to the underlying xarray object
    # ------------------------------------------------------------------
    @property
    def xr(self) -> xr.Dataset:
        """The wrapped :class:`xarray.Dataset`.

        Treat as read-only from the outside; processing nodes should
        return *new* :class:`Dataset` instances (see :meth:`copy_with`)
        rather than mutating in place, so the original stays usable for
        provenance, caching and undo.
        """

        return self._data

    @property
    def dims(self) -> tuple[str, ...]:
        return tuple(self._data.dims)

    # ------------------------------------------------------------------
    # Axis role bookkeeping
    # ------------------------------------------------------------------
    def set_axis_meta(self, name: str, meta: AxisMeta) -> None:
        if (
            name not in self._data.dims
            and name not in self._data.coords
            and name not in self._data.variables
        ):
            raise KeyError(
                f"'{name}' is not a dimension, coordinate or variable of "
                f"this dataset"
            )
        self._axis_meta[name] = meta

    def set_axis_role(
        self,
        name: str,
        role: AxisRole,
        unit: str | None = None,
        label: str | None = None,
        custom_role: str | None = None,
    ) -> None:
        self.set_axis_meta(
            name,
            AxisMeta(
                name=name, role=role, unit=unit, label=label,
                custom_role=custom_role,
            ),
        )

    def get_axis_meta(self, name: str) -> AxisMeta:
        return self._axis_meta.get(name, AxisMeta(name=name))

    def axes_with_role(
        self, role: AxisRole, custom_role: str | None = None
    ) -> list[str]:
        """Return all axis names tagged with ``role``.

        If ``role`` is :data:`AxisRole.CUSTOM`, ``custom_role`` selects a
        specific domain-defined role string.
        """

        result = []
        for name, meta in self._axis_meta.items():
            if meta.role is not role:
                continue
            if role is AxisRole.CUSTOM and meta.custom_role != custom_role:
                continue
            result.append(name)
        return result

    def primary_axis(
        self, role: AxisRole, custom_role: str | None = None
    ) -> str | None:
        """Convenience wrapper: return the first axis with ``role``, or
        ``None`` if there is none."""
        axes = self.axes_with_role(role, custom_role=custom_role)
        return axes[0] if axes else None

    # ------------------------------------------------------------------
    # Serialisation (for project files / templates / caching)
    # ------------------------------------------------------------------
    def axis_meta_dict(self) -> dict[str, dict[str, Any]]:
        return {name: meta.to_dict() for name, meta in self._axis_meta.items()}

    @classmethod
    def from_xarray(
        cls,
        data: xr.Dataset,
        axis_meta_dict: dict[str, dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Dataset":
        axis_meta = {
            name: AxisMeta.from_dict(d)
            for name, d in (axis_meta_dict or {}).items()
        }
        return cls(data, axis_meta=axis_meta, metadata=metadata)

    def copy_with(self, data: xr.Dataset) -> "Dataset":
        """Return a new :class:`Dataset` with new underlying data, keeping
        axis metadata for any names that still apply.

        Processing nodes should use this rather than mutating ``self`` in
        place: it keeps the input dataset valid (e.g. for caching/undo)
        and carries over axis-role tags automatically wherever the
        dimension/coordinate/variable names are unchanged.
        """

        new_axis_meta = {
            name: meta
            for name, meta in self._axis_meta.items()
            if name in data.dims or name in data.coords or name in data.variables
        }
        return Dataset(data, axis_meta=new_axis_meta, metadata=dict(self.metadata))
