"""Base class for dockable tool-panel plugins.

A panel is a :class:`QWidget` shown inside a :class:`QDockWidget` of the
main window - e.g. a project explorer, the workflow graph editor, a
properties inspector, or a provenance/lineage viewer. Third-party
plugins register subclasses of :class:`PanelPlugin` the same way core
panels do; :class:`alchemetra.ui.main_window.MainWindow` discovers all
registered panels via :class:`~alchemetra.plugins.registry.PluginRegistry`
and creates one dock widget per panel at startup.
"""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from ...plugins.base import PluginBase, PluginKind
from ..context import UiContext


class PanelPlugin(PluginBase):
    """Base class for a dockable tool panel.

    Subclasses must implement :meth:`create_widget`. Everything else has
    sensible defaults so a minimal panel only needs ``plugin_id``,
    ``display_name`` and :meth:`create_widget`.
    """

    plugin_kind: ClassVar[PluginKind] = PluginKind.PANEL

    #: Which edge of the main window this panel docks to by default. The
    #: user can move it afterwards; this is only the initial placement.
    default_area: ClassVar[Qt.DockWidgetArea] = Qt.DockWidgetArea.LeftDockWidgetArea

    #: Whether this panel is shown by default on first launch.
    default_visible: ClassVar[bool] = True

    def create_widget(self, context: UiContext) -> QWidget:
        """Create and return the panel's content widget.

        ``context`` gives access to the current project, annotation
        service and cross-panel signals - see
        :class:`alchemetra.ui.context.UiContext`. Implementations should
        connect to ``context``'s signals to stay in sync rather than
        polling.
        """

        raise NotImplementedError
