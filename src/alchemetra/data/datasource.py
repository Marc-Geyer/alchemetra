"""Base class for data-source plugins.

A data source is the entry point of (almost) every workflow graph - it
has no inputs and produces one or more :class:`Artifact` instances.

Concrete data sources (Raman .spc readers, generic CSV/Excel importers,
electrochemical exporters, ...) are shipped as default plugins but are
not special in any way - users can add their own.
"""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from ..plugins.base import PluginBase, PluginKind
from .artifact import Artifact


class DataSourcePlugin(PluginBase):
    """Base class for anything that can load data into the project."""

    plugin_kind: ClassVar[PluginKind] = PluginKind.DATA_SOURCE

    #: File extensions this loader can handle (without the leading dot),
    #: used by the UI to populate "open file" dialogs / drag-and-drop
    #: dispatch. Leave empty for sources that are not file based (e.g.
    #: instrument live-acquisition).
    file_extensions: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def load(self, source: Path | str, **options: Any) -> dict[str, Artifact]:
        """Load ``source`` and return one or more named artifacts.

        Returning a ``dict`` (rather than a single artifact) lets a
        single file produce several logical datasets - e.g. a combined
        instrument export that contains both spectra and electrochemical
        channels, which should become independently usable artifacts in
        the project.
        """

        ...

    @classmethod
    def supports(cls, source: Path | str) -> bool:
        """Default extension-based check; override for smarter sniffing
        (e.g. magic bytes, header inspection)."""

        suffix = Path(source).suffix.lstrip(".").lower()
        return suffix in cls.file_extensions
