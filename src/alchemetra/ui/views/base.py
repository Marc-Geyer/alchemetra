"""ViewPlugin – base class for artifact view plugins."""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtWidgets import QWidget

from ...data.artifact import Artifact
from ...plugins.base import PluginBase, PluginKind
from ..context import UiContext


class ViewPlugin(PluginBase):
    """Subclass this to add a new artifact visualisation to the central tab area.

    Plugin interface
    ----------------
    plugin_id      : str   – unique reverse-domain id
    display_name   : str   – shown in tab title
    priority       : int   – tie-break when multiple views support the same artifact
    supports(artifact) -> bool
        Check by AxisRole, never by dimension name.
    create_widget(artifact, context) -> QWidget
    """

    plugin_kind: ClassVar[PluginKind] = PluginKind.VISUALIZATION
    priority: ClassVar[int] = 0

    @classmethod
    def supports(cls, artifact: Artifact) -> bool:
        raise NotImplementedError

    def create_widget(self, artifact: Artifact, context: UiContext) -> QWidget:
        raise NotImplementedError
