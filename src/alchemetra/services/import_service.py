"""ImportService: load files through DataSourcePlugins into a Project."""

from __future__ import annotations

from pathlib import Path

from ..data.artifact import Artifact
from ..data.datasource import DataSourcePlugin
from ..plugins.base import PluginKind
from ..plugins.registry import PluginRegistry
from ..project.project import Project


class ImportService:
    @staticmethod
    def supported_extensions() -> list[str]:
        from ..builtin import register_all
        register_all()
        return sorted(
            {
                ext
                for plugin_cls in PluginRegistry.all(PluginKind.DATA_SOURCE)
                for ext in plugin_cls.file_extensions
            }
        )

    @staticmethod
    def find_plugin(
        path: str | Path,
    ) -> type[DataSourcePlugin] | None:
        from ..builtin import register_all
        register_all()
        for plugin_cls in PluginRegistry.all(PluginKind.DATA_SOURCE):
            if plugin_cls.supports(str(path)):
                return plugin_cls
        return None

    @staticmethod
    def import_file(
        project: Project,
        path: str | Path,
        **options,
    ) -> list[Artifact]:
        """Load ``path`` and register each returned artifact as raw data
        behind its own workflow entry node."""

        plugin_cls = ImportService.find_plugin(path)
        if plugin_cls is None:
            raise ValueError(f"No data source plugin supports '{Path(path).name}'")
        loaded = plugin_cls().load(str(path), **options)
        stem = Path(path).stem
        artifacts = []
        for port, artifact in loaded.items():
            base = stem if len(loaded) == 1 else f"{stem}_{port}"
            project.add_raw_data(
                project.unique_node_id(base), artifact, plugin_id=plugin_cls.plugin_id
            )
            artifacts.append(artifact)
        return artifacts
