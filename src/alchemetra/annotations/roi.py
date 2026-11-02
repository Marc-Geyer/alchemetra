"""Region-of-interest annotation: a rectangular range over one or more
axes, identified by their semantic roles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from ..data.dataset import AxisRole
from ..plugins.registry import register_plugin
from .base import AnnotationBase


@register_plugin
@dataclass
class ROIAnnotation(AnnotationBase):
    plugin_id: ClassVar[str] = "core.annotation.roi"
    display_name: ClassVar[str] = "Region of interest"

    #: (min, max) bounds per axis role, e.g.
    #: ``{AxisRole.SPECTRAL: (1000, 1200), AxisRole.TEMPORAL: (0, 60)}``
    bounds: dict[AxisRole, tuple[float, float]] = field(default_factory=dict)

    def axis_roles(self) -> tuple[AxisRole, ...]:
        return tuple(self.bounds.keys())

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["bounds"] = {
            role.name: list(bounds) for role, bounds in self.bounds.items()
        }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ROIAnnotation":
        data = dict(data)
        data.pop("plugin_id", None)
        data["bounds"] = {
            AxisRole[role]: tuple(bounds)
            for role, bounds in data.get("bounds", {}).items()
        }
        return cls(**data)
