"""MainWindow – thin shell hosting dockable panels and tabbed artifact views."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QWidget,
)

from ..data.artifact import Artifact
from ..plugins.base import PluginKind
from ..plugins.registry import PluginRegistry
from ..project.project import Project
from ..project.project_manager import ProjectManager
from ..services.import_service import ImportService
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

        self._open_views: dict[str, QWidget] = {}
        self._docks: dict[str, QDockWidget] = {}

        self._build_menus()
        self.reload_panels()
        self.context.view_requested.connect(self.open_view_for_artifact)

    # ------------------------------------------------------------------
    def _build_menus(self) -> None:
        mb = self.menuBar()
        file_menu = mb.addMenu("&File")
        file_menu.addAction("&New Project", self.new_project)
        file_menu.addAction("&Open Project\u2026", self.open_project_dialog)
        file_menu.addAction("&Save Project As\u2026", self.save_project_dialog)
        file_menu.addSeparator()
        file_menu.addAction("&Import Data\u2026", self.import_data_dialog)
        file_menu.addSeparator()
        file_menu.addAction("Export Workflow &Template\u2026", self.export_template_dialog)
        file_menu.addAction("Load Workflow T&emplate\u2026", self.load_template_dialog)
        file_menu.addSeparator()
        file_menu.addAction("&Run Workflow", self.run_workflow)
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close)
        self.view_menu = mb.addMenu("&View")

    def reload_panels(self) -> None:
        """Discover and create dock widgets for all registered PanelPlugins.

        Safe to call again at runtime after new panel plugins are registered –
        existing panels are not duplicated.
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
    def open_view_for_artifact(self, artifact_id: str) -> None:
        artifact = self.context.artifact(artifact_id)
        if artifact is None:
            return

        existing = self._open_views.get(artifact_id)
        if existing is not None:
            idx = self._tabs.indexOf(existing)
            if idx != -1:
                self._tabs.setCurrentIndex(idx)
                return
            del self._open_views[artifact_id]

        plugin_cls = self._best_view_for(artifact)
        if plugin_cls is None:
            QMessageBox.information(
                self, "No view available",
                f"No view plugin can display '{artifact.label}'.",
            )
            return

        plugin = plugin_cls()
        widget = plugin.create_widget(artifact, self.context)
        title = f"{artifact.label} – {plugin.display_name}"
        idx = self._tabs.addTab(widget, title)
        self._tabs.setCurrentIndex(idx)
        self._open_views[artifact_id] = widget

    @staticmethod
    def _best_view_for(artifact: Artifact):
        candidates = [
            p for p in PluginRegistry.all(PluginKind.VISUALIZATION)
            if p.supports(artifact)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda p: p.priority, reverse=True)
        return candidates[0]

    def _close_tab(self, index: int) -> None:
        widget = self._tabs.widget(index)
        self._tabs.removeTab(index)
        for aid, w in list(self._open_views.items()):
            if w is widget:
                del self._open_views[aid]
        if widget is not None:
            widget.deleteLater()

    # ------------------------------------------------------------------
    def _reset_views(self) -> None:
        self._tabs.clear()
        self._open_views.clear()

    def new_project(self) -> None:
        self.context.set_project(Project())
        self._reset_views()

    # -- path-based operations (raise on error; used by dialogs and tests) --
    def save_project(self, path: str | Path) -> None:
        ProjectManager.save(self.context.project, path)

    def open_project(self, path: str | Path) -> None:
        self.context.set_project(ProjectManager.load(path))
        self._reset_views()

    def import_file(self, path: str | Path, **options) -> None:
        artifacts = ImportService.import_file(self.context.project, path, **options)
        self.context.notify_workflow_changed()
        if artifacts:
            self.context.request_view(artifacts[0].id)

    def export_template(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.context.project.export_template(), indent=2))

    def load_template(self, path: str | Path) -> None:
        """Replace the workflow with a template; the project's current raw
        data stays attached to the entry nodes with matching ids."""
        self.context.project.import_template(json.loads(Path(path).read_text()))
        self.context.notify_workflow_changed()

    # -- dialog wrappers ------------------------------------------------
    def _guard(self, title: str, action: Callable[[], None]) -> None:
        try:
            action()
        except Exception as exc:  # noqa: BLE001 - surface to the user
            QMessageBox.critical(self, title, str(exc))

    def save_project_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Save project to folder")
        if path:
            self._guard("Saving failed", lambda: self.save_project(path))

    def open_project_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Open project folder")
        if path:
            self._guard("Opening failed", lambda: self.open_project(path))

    def import_data_dialog(self) -> None:
        exts = " ".join(f"*{e}" for e in ImportService.supported_extensions())
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import data", "", f"Data files ({exts});;All files (*)")
        for path in paths:
            self._guard("Import failed", lambda p=path: self.import_file(p))

    def export_template_dialog(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export workflow template", "workflow.json", "Template (*.json)")
        if path:
            self._guard("Export failed", lambda: self.export_template(path))

    def load_template_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load workflow template", "", "Template (*.json)")
        if path:
            self._guard("Loading template failed", lambda: self.load_template(path))

    def run_workflow(self) -> None:
        try:
            self.context.project.run()
        except Exception as exc:  # noqa: BLE001 - surface to the user
            QMessageBox.critical(self, "Workflow failed", str(exc))
            return
        self.context.notify_workflow_changed()
