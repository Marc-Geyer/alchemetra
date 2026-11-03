"""Separator annotation: a single cut line along an axis, used to split a
dataset into independent segments (e.g. separating concatenated
measurement runs)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data.dataset import AxisRole
from ..plugins.registry import register_plugin
from .base import AnnotationBase


@register_plugin
@dataclass
class SeparatorAnnotation(AnnotationBase):
    plugin_id = "core.annotation.separator"
    display_name = "Separator"

    #: Position of the cut, in native units of the chosen axis.
    position: float = 0.0

    #: Which axis role this separator cuts along.
    axis_role: AxisRole = AxisRole.TEMPORAL

    def axis_roles(self) -> tuple[AxisRole, ...]:
        return (self.axis_role,)
