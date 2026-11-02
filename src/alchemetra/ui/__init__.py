"""PySide6 user interface for Alchemetra.

This package contains only the *shell*: a main window that hosts
dockable tool panels and tabbed/MDI artifact views, plus the plugin base
classes (:mod:`alchemetra.ui.panels.base`,
:mod:`alchemetra.ui.views.base`) that let third-party plugins contribute
their own widgets without touching this code.

Layout, styling and behaviour are loosely inspired by PyCharm's
tool-window model: panels dock to the edges of the main window, can be
hidden/shown via the "View" menu, and the centre is a tabbed area of
artifact views.
"""

from __future__ import annotations
