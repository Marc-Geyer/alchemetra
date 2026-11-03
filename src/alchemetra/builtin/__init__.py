"""Built-in default plugins shipped with Alchemetra.

Importing the submodules registers the default data-source, processing-node
and annotation plugins with
:class:`~alchemetra.plugins.registry.PluginRegistry`. Third-party and
domain-specific plugins live in separate packages and register themselves
the same way.
"""

from __future__ import annotations


def register_all() -> None:
    """Register the built-in default plugins.

    Safe to call multiple times (subsequent imports are no-ops thanks to
    Python's module cache).
    """

    from . import (  # noqa: F401
        csv_source,
        example_nodes,
        processing_nodes,
    )
    from ..annotations import (  # noqa: F401
        peak,
        roi,
        separator,
    )
