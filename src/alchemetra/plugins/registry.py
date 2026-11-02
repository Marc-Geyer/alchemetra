"""Central registry that the application core uses to discover plugins.

Plugins register themselves via the :func:`register_plugin` decorator.
The registry is intentionally simple (a nested dict) so it is trivial to
extend with e.g. entry-point based discovery later without touching any
of the call sites.
"""

from __future__ import annotations

from typing import Iterable

from .base import PluginBase, PluginKind


class PluginRegistrationError(Exception):
    """Raised when a plugin cannot be registered (e.g. duplicate id)."""


class PluginRegistry:
    """Process-wide registry of available plugin classes."""

    _plugins: dict[PluginKind, dict[str, type[PluginBase]]] = {
        kind: {} for kind in PluginKind
    }

    @classmethod
    def register(cls, plugin_cls: type[PluginBase]) -> type[PluginBase]:
        kind = plugin_cls.plugin_kind
        plugin_id = plugin_cls.plugin_id

        existing = cls._plugins[kind].get(plugin_id)
        if existing is not None and existing is not plugin_cls:
            raise PluginRegistrationError(
                f"Plugin id '{plugin_id}' already registered for "
                f"{kind.name} by {existing!r}"
            )

        cls._plugins[kind][plugin_id] = plugin_cls
        return plugin_cls

    @classmethod
    def unregister(cls, kind: PluginKind, plugin_id: str) -> None:
        cls._plugins[kind].pop(plugin_id, None)

    @classmethod
    def get(cls, kind: PluginKind, plugin_id: str) -> type[PluginBase]:
        try:
            return cls._plugins[kind][plugin_id]
        except KeyError as exc:
            raise KeyError(
                f"No {kind.name} plugin registered with id '{plugin_id}'"
            ) from exc

    @classmethod
    def all(cls, kind: PluginKind) -> Iterable[type[PluginBase]]:
        return cls._plugins[kind].values()

    @classmethod
    def describe_all(cls, kind: PluginKind) -> list[dict]:
        return [p.describe() for p in cls.all(kind)]


def register_plugin(plugin_cls: type[PluginBase]) -> type[PluginBase]:
    """Class decorator: register a plugin with the global registry.

    Example
    -------
    >>> @register_plugin
    ... class MovingAverage(NodeBase):
    ...     plugin_id = "core.moving_average"
    ...     ...
    """

    return PluginRegistry.register(plugin_cls)
