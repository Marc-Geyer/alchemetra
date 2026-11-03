"""Built-in panel and view plugins.

Importing this module registers all of Alchemetra's default UI plugins
(project explorer, properties, workflow, node inspector panels; spectrum,
heatmap and table views) with the plugin registry, via the built-in core
plugins.
"""

from __future__ import annotations


def register_all() -> None:
    """Import every built-in plugin module so their
    ``@register_plugin`` decorators run.

    Safe to call multiple times (subsequent imports are no-ops).
    """

    from ...builtin import register_all as register_core
    register_core()
    from . import (  # noqa: F401
        heatmap_view,
        node_inspector_panel,
        project_panel,
        properties_panel,
        spectrum_view,
        table_view,
        workflow_panel,
    )
