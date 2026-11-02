"""The main application window.

:class:`MainWindow` is intentionally thin: it owns a
:class:`~alchemetra.ui.context.UiContext`, lays out dockable panels
(discovered from :class:`~alchemetra.plugins.registry.PluginRegistry` via
:class:`~alchemetra.ui.panels.base.PanelPlugin`), and a tabbed central
area for artifact views (:class:`~alchemetra.ui.views.base.ViewPlugin`).
It contains no domain logic - that all lives in the core
(:mod:`alchemetra.project`, :mod:`alchemetra.workflow`, ...) and in
panel/view plugins.

Adding a new panel or view, including from a third-party plugin package,
only requires registering a :class:`PanelPlugin`/:class:`ViewPlugin`
subclass with :class:`PluginRegistry` *before* :class:`MainWindow` is
constructed (or before :meth:`MainWindow.reload_panels` is called) -
nothing here needs to change.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QWidget,
)

from ..data.artifact import Artifact
from ..plugins.base import PluginKind
from ..plugins.registry import PluginRegistry
from ..project.project import Project
from .context import UiContext


class MainWindow(QMainWindow):
    def __init__(self, context: UiContext | None = None) -> None:
        super().__init__()
        self.context = context or UiContext()

        self.setWindowTitle("Alchemetra")
        self.resize(1280, 800)

        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self._tabs)

        #: artifact id -> widget currently showing it (one view per
        #: artifact at a time; re-requesting just focuses the tab).
        self._open_views: dict[str, QWidget] = {}

        self._docks: dict[str, QDockWidget] = {}

        self._build_menus()
        self.reload_panels()

        self.context.view_requested.connect(self.open_view_for_artifact)

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------
    def _build_menus(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("&New Project", self.new_project)
        file_menu.addSeparator()
        file_menu.addAction("&Run Workflow", self.run_workflow)
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close)

        #: Populated by :meth:`reload_panels` with one "toggle visible"
        #: action per dock widget.
        self.view_menu = menu_bar.addMenu("&View")

    # ------------------------------------------------------------------
    # Panels
    # ------------------------------------------------------------------
    def reload_panels(self) -> None:
        """(Re)create one dock widget per registered
        :class:`~alchemetra.ui.panels.base.PanelPlugin`.

        Safe to call again after new panel plugins are registered at
        runtime - existing docks for plugin ids that are already present
        are left untouched.
        """

        from .builtin import register_all

        register_all()

        for plugin_cls in PluginRegistry.all(PluginKind.PANEL):
            if plugin_cls.plugin_id in self._docks:
                continue

            plugin = plugin_cls()
            widget = plugin.create_widget(self.context)

            dock = QDockWidget(plugin.display_name, self)
            dock.setObjectName(plugin.plugin_id)
            dock.setWidget(widget)
            self.addDockWidget(plugin.default_area, dock)
            if not plugin.default_visible:
                dock.hide()

            self.view_menu.addAction(dock.toggleViewAction())
            self._docks[plugin.plugin_id] = dock

    # ------------------------------------------------------------------
    # Artifact views
    # ------------------------------------------------------------------
    def open_view_for_artifact(self, artifact_id: str) -> None:
        """Open (or focus) a view for the artifact with the given id.

        The view plugin is chosen from every registered
        :class:`~alchemetra.ui.views.base.ViewPlugin` whose
        :meth:`~alchemetra.ui.views.base.ViewPlugin.supports` returns
        ``True`` for this artifact, picking the highest
        :attr:`~alchemetra.ui.views.base.ViewPlugin.priority`. If no
        plugin supports the artifact, the user is informed - this is
        expected for artifacts that aren't meant to be visualised
        directly (e.g. pure metadata/results).
        """

        artifact = self.context.artifact(artifact_id)
        if artifact is None:
            return

        existing = self._open_views.get(artifact_id)
        if existing is not None:
            index = self._tabs.indexOf(existing)
            if index != -1:
                self._tabs.setCurrentIndex(index)
                return
            # Tab was closed without going through _close_tab somehow.
            del self._open_views[artifact_id]

        plugin_cls = self._best_view_for(artifact)
        if plugin_cls is None:
            QMessageBox.information(
                self,
                "No view available",
                f"No view plugin can currently display '{artifact.label}'.",
            )
            return

        plugin = plugin_cls()
        widget = plugin.create_widget(artifact, self.context)
        index = self._tabs.addTab(widget, f"{artifact.label} \u2013 {plugin.display_name}")
        self._tabs.setCurrentIndex(index)
        self._open_views[artifact_id] = widget

    @staticmethod
    def _best_view_for(artifact: Artifact):
        candidates = [
            plugin_cls
            for plugin_cls in PluginRegistry.all(PluginKind.VISUALIZATION)
            if plugin_cls.supports(artifact)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda p: p.priority, reverse=True)
        return candidates[0]

    def _close_tab(self, index: int) -> None:
        widget = self._tabs.widget(index)
        self._tabs.removeTab(index)
        for artifact_id, open_widget in list(self._open_views.items()):
            if open_widget is widget:
                del self._open_views[artifact_id]
        if widget is not None:
            widget.deleteLater()

    # ------------------------------------------------------------------
    # Project actions
    # ------------------------------------------------------------------
    def new_project(self) -> None:
        self.context.set_project(Project())
        self._tabs.clear()
        self._open_views.clear()

    def run_workflow(self) -> None:
        try:
            self.context.project.run()
        except Exception as exc:  # noqa: BLE001 - surface to the user
            QMessageBox.critical(self, "Workflow failed", str(exc))
            return
        self.context.notify_workflow_changed()
