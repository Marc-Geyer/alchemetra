"""Base class for artifact view plugins.

A view renders one :class:`~alchemetra.data.artifact.Artifact` - e.g. a
1D spectrum plot, a 2D time-spectra heatmap, or a future table/3D view.
Views are matched to artifacts via :meth:`ViewPlugin.supports`, which
inspects the dataset's :class:`~alchemetra.data.dataset.AxisRole` tags
rather than any hardcoded dimension name or domain assumption - this is
what lets the same heatmap view work for a Raman time-series or a
chromatography-vs-time dataset without modification.

:class:`alchemetra.ui.main_window.MainWindow` opens views by asking the
plugin registry for every registered :class:`ViewPlugin`, filtering to
those whose :meth:`supports` returns ``True`` for the artifact, and (if
more than one matches) picking the highest :attr:`priority` - or letting
the user choose.
"""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtWidgets import QWidget

from ...data.artifact import Artifact
from ...plugins.base import PluginBase, PluginKind
from ..context import UiContext


class ViewPlugin(PluginBase):
    """Base class for a widget that visualises one artifact.

    Subclasses must implement :meth:`supports` and
    :meth:`create_widget`.
    """

    plugin_kind: ClassVar[PluginKind] = PluginKind.VISUALIZATION

    #: Used to break ties when several view plugins support the same
    #: artifact - higher wins as the default choice.
    priority: ClassVar[int] = 0

    @classmethod
    def supports(cls, artifact: Artifact) -> bool:
        """Return ``True`` if this view can meaningfully display
        ``artifact``.

        Implementations should check :meth:`Dataset.axes_with_role`
        rather than dimension names or variable names, so the check
        stays valid across domains.
        """

        raise NotImplementedError

    def create_widget(self, artifact: Artifact, context: UiContext) -> QWidget:
        """Create and return a widget displaying ``artifact``.

        The returned widget is placed in a new tab of the main window's
        central view area. Implementations should connect to
        ``context``'s signals (e.g. ``annotations_changed``) if the view
        needs to react to changes made elsewhere.
        """

        raise NotImplementedError
