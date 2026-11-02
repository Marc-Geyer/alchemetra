"""Separator annotation: a single cut line along an axis, used to split a
dataset into independent segments (e.g. separating concatenated
measurement runs)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ..data.dataset import AxisRole
from ..plugins.registry import register_plugin
from .base import AnnotationBase


@register_plugin
@dataclass
class SeparatorAnnotation(AnnotationBase):
    plugin_id: ClassVar[str] = "core.annotation.separator"
    display_name: ClassVar[str] = "Separator"

    #: Position of the cut, in native units of the chosen axis.
    position: float = 0.0

    #: Which axis role this separator cuts along.
    axis_role: AxisRole = AxisRole.TEMPORAL

    def axis_roles(self) -> tuple[AxisRole, ...]:
        return (self.axis_role,)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["axis_role"] = self.axis_role.name
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SeparatorAnnotation":
        data = dict(data)
        data.pop("plugin_id", None)
        data["axis_role"] = AxisRole[data["axis_role"]]
        return cls(**data)
