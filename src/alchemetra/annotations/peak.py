"""Peak annotation: a single point of interest along a spectral axis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ..data.dataset import AxisRole
from ..plugins.registry import register_plugin
from .base import AnnotationBase


@register_plugin
@dataclass
class PeakAnnotation(AnnotationBase):
    plugin_id: ClassVar[str] = "core.annotation.peak"
    display_name: ClassVar[str] = "Peak"

    #: Position along the spectral axis, in its native units.
    position: float = 0.0

    #: Optional width estimate (e.g. FWHM), same units as position.
    width: float | None = None

    def axis_roles(self) -> tuple[AxisRole, ...]:
        return (AxisRole.SPECTRAL,)
