"""Region-of-interest annotation: a rectangular range over one or more
axes, identified by their semantic roles."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data.dataset import AxisRole
from ..plugins.registry import register_plugin
from .base import AnnotationBase


@register_plugin
@dataclass
class ROIAnnotation(AnnotationBase):
    plugin_id = "core.annotation.roi"
    display_name = "Region of interest"

    #: (min, max) bounds per axis role, e.g.
    #: ``{AxisRole.SPECTRAL: (1000, 1200), AxisRole.TEMPORAL: (0, 60)}``
    bounds: dict = field(default_factory=dict)

    def axis_roles(self) -> tuple[AxisRole, ...]:
        return tuple(AxisRole[k] for k in self.bounds)
