"""Annotations: user-created markers on data (peaks, ROIs, separators, ...).

Like processing nodes, annotation types are plugins. The base class fixes
how an annotation refers to axes (via
:class:`~alchemetra.data.dataset.AxisRole`, never a hardcoded dimension
name) and how it is (de)serialised so it can live in a project file and
be re-applied to any dataset with matching axis roles - including ones
from a different domain.
"""

from __future__ import annotations

import uuid
from abc import abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar

from ..data.dataset import AxisRole, Dataset
from ..plugins.base import PluginBase, PluginKind


@dataclass
class AnnotationBase(PluginBase):
    """Base class for one annotation instance.

    Subclasses are dataclasses describing the annotation's geometry (a
    peak's position/width, an ROI's bounds, ...) in terms of *axis
    roles*, not literal dimension names. :meth:`resolve` maps those roles
    onto the dimension names of a concrete dataset.
    """

    plugin_kind: ClassVar[PluginKind] = PluginKind.ANNOTATION

    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    #: Which artifact this annotation was created on - kept for display
    #: purposes; :meth:`resolve` can be used against *any* compatible
    #: dataset.
    artifact_id: str | None = None

    #: Free-form label/colour/etc. for the UI.
    metadata: dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def axis_roles(self) -> tuple[AxisRole, ...]:
        """Return the axis roles this annotation is defined against.

        E.g. a peak on a spectrum returns ``(AxisRole.SPECTRAL,)``; a
        time-window ROI on a heatmap might return
        ``(AxisRole.SPECTRAL, AxisRole.TEMPORAL)``.
        """

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

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["plugin_id"] = self.plugin_id
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnnotationBase":
        data = dict(data)
        data.pop("plugin_id", None)
        return cls(**data)

    id: str = field(default_factory=lambda: str(uuid4()))

    label: str = ""