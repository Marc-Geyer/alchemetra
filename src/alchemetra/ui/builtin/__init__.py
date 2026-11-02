"""Built-in panel and view plugins.

Importing this module registers all of Alchemetra's default UI plugins
(project explorer, properties, workflow panels; spectrum and heatmap
views) with :class:`~alchemetra.plugins.registry.PluginRegistry`. Each
submodule is independent and only depends on the base classes in
:mod:`alchemetra.ui.panels.base` / :mod:`alchemetra.ui.views.base` -
third-party plugins can follow the same pattern from outside this
package.
"""

from __future__ import annotations


def register_all() -> None:
    """Import every built-in panel/view module so their
    ``@register_plugin`` decorators run.

    Safe to call multiple times (subsequent imports are no-ops).
    """

    from . import (  # noqa: F401
        heatmap_view,
        project_panel,
        properties_panel,
        spectrum_view,
        workflow_panel,
    )
