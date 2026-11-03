"""PanelPlugin – base class for dockable tool-panel plugins."""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from ...plugins.base import PluginBase, PluginKind
from ..context import UiContext


class PanelPlugin(PluginBase):
    """Subclass this to add a dockable panel to the main window.

    Plugin interface
    ----------------
    plugin_id     : str          – unique reverse-domain id
    display_name  : str          – shown in the dock title bar and View menu
    default_area  : Qt.DockWidgetArea – initial dock position (default: Left)
    default_visible : bool       – shown on first launch (default: True)
    create_widget(context) -> QWidget
    """

    plugin_kind: ClassVar[PluginKind] = PluginKind.PANEL
    default_area: ClassVar[Qt.DockWidgetArea] = Qt.DockWidgetArea.LeftDockWidgetArea
    default_visible: ClassVar[bool] = True

    def create_widget(self, context: UiContext) -> QWidget:
        raise NotImplementedError
