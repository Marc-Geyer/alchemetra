"""Base class for annotation plugins."""

from __future__ import annotations

import dataclasses
import uuid
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..data.dataset import AxisRole, Dataset
from ..plugins.base import PluginBase, PluginKind
from ..plugins.registry import PluginRegistry

_ENUMS = {"AxisRole": AxisRole}


def _encode(value: Any) -> Any:
    if isinstance(value, Enum):
        return {"__enum__": type(value).__name__, "name": value.name}
    if isinstance(value, dict):
        return {
            (k.name if isinstance(k, Enum) else str(k)): _encode(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_encode(v) for v in value]
    return value


def _decode(value: Any) -> Any:
    if isinstance(value, dict):
        if "__enum__" in value:
            return _ENUMS[value["__enum__"]][value["name"]]
        return {k: _decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode(v) for v in value]
    return value


@dataclass
class AnnotationBase(PluginBase):
    """Base class for one annotation instance.

    Subclasses are dataclasses describing the annotation's geometry (a
    peak's position/width, an ROI's bounds, ...) in terms of *axis
    roles*, not literal dimension names. :meth:`resolve` maps those roles
    onto the dimension names of a concrete dataset.
    """

    plugin_kind = PluginKind.ANNOTATION

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    artifact_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def axis_roles(self) -> tuple[AxisRole, ...]:
        """Return the axis roles this annotation is defined against.

        E.g. a peak on a spectrum returns ``(AxisRole.SPECTRAL,)``; a
        time-window ROI on a heatmap might return
        ``(AxisRole.SPECTRAL, AxisRole.TEMPORAL)``.
        """

        raise NotImplementedError

    def resolve(self, dataset: Dataset) -> dict[AxisRole, str]:
        """Map this annotation's required roles onto dimension names of
        ``dataset``.

        Raises ``ValueError`` if a required role is not present - this is
        how the platform detects "this annotation doesn't make sense for
        this dataset" without any domain-specific checks.
        """

        mapping: dict[AxisRole, str] = {}
        for role in self.axis_roles():
            axis = dataset.primary_axis(role)
            if axis is None:
                raise ValueError(
                    f"Dataset has no axis with role {role.name}, required "
                    f"by annotation '{self.plugin_id}'"
                )
            mapping[role] = axis
        return mapping

    # -- serialisation (generic: works for any dataclass-based annotation) --
    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "fields": {
                f.name: _encode(getattr(self, f.name)) for f in dataclasses.fields(self)
            },
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AnnotationBase":
        """Rebuild an annotation via the plugin registry (third-party
        annotation plugins are supported automatically)."""

        plugin_cls = PluginRegistry.get(PluginKind.ANNOTATION, data["plugin_id"])
        return plugin_cls(**_decode(data["fields"]))
