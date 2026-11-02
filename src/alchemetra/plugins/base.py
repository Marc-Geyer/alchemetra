"""Core plugin abstractions.

Every functional module of Alchemetra (data sources, processing nodes,
annotation types, exporters, ...) is implemented as a *plugin*: a small
class that the application core knows nothing about until it is
registered. This keeps the core minimal and makes every feature
(including the ones shipped "by default") optional and replaceable.
"""

from __future__ import annotations

from abc import ABC
from enum import Enum, auto
from typing import Any, ClassVar


class PluginKind(Enum):
    """Categories of plugins the application core knows how to host."""

    DATA_SOURCE = auto()
    PROCESSING_NODE = auto()
    ANNOTATION = auto()
    VISUALIZATION = auto()
    EXPORTER = auto()

    #: Dockable tool panels hosted in the main window (project explorer,
    #: workflow editor, properties, ...). See
    #: :mod:`alchemetra.ui.panels.base`.
    PANEL = auto()


class PluginBase(ABC):
    """Common interface every plugin must implement.

    Subclasses are expected to set the class attributes below. They are
    declared as ``ClassVar`` because they describe the *type* of plugin,
    not a particular instance.
    """

    #: Unique, stable identifier used in templates / project files.
    #: Must never change once shipped, or saved templates break.
    plugin_id: ClassVar[str]

    #: Which registry this plugin belongs to.
    plugin_kind: ClassVar[PluginKind]

    #: Human readable name shown in the UI.
    display_name: ClassVar[str] = ""

    #: Free-form version string, useful for migrations of saved templates.
    version: ClassVar[str] = "0.1.0"

    #: Optional short description shown as a tooltip in the UI.
    description: ClassVar[str] = ""

    @classmethod
    def describe(cls) -> dict[str, Any]:
        """Return a JSON-serialisable description of this plugin type.

        Used by the UI to populate palettes/menus without instantiating
        the plugin, and stored alongside templates for human-readable
        debugging.
        """

        return {
            "plugin_id": cls.plugin_id,
            "plugin_kind": cls.plugin_kind.name,
            "display_name": cls.display_name or cls.plugin_id,
            "version": cls.version,
            "description": cls.description,
        }
