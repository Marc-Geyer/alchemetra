# Plugin Development Guide

How to add new capabilities to Alchemetra by implementing a **default
plugin**, and how to structure **third-party plugins**.

The platform is *plugin-first*: the core knows nothing about concrete
domain behaviour. Every feature ships as a plugin registered in the global
`PluginRegistry`.

## Prerequisites for plugin authors

- Python >= 3.11
- Familiarity with the relevant core abstraction (see [API.md](API.md))
- For UI plugins: PySide6 / Qt knowledge

## General rules for every plugin

1. **Subclass the right base** for your kind (see table below).
2. **Set `plugin_id`** — a *stable, unique, snake_case identifier* of the
   form `core.<kind_category>.<snake_case_name>`, e.g. `core.source.csv`.
   `plugin_id` is used in templates and project files and must not change
   once released (or saved templates will break).
3. **Set `display_name`** — human-readable, shown in UI.
4. **Set `version`** — free-form version string, used for migrations of
   saved templates.
5. **Set `description`** — short tooltip/description.
6. **Register** with the `@register_plugin` class decorator (or
   `PluginRegistry.register`).

```python
from alchemetra.plugins.registry import register_plugin

@register_plugin
class MyThing(MyBase):
    plugin_id = "core.something.mything"
    ...
```

7. **Import your module** for registration to run (e.g. import from your
   plugin package, or call `alchemetra.builtin.register_all()` /
   `alchemetra.ui.builtin.register_all()` for built-ins).

## Plugin kinds

| Kind | Base class | Use it for | Contract highlights |
|---|---|---|---|
| `DATA_SOURCE` | `DataSourcePlugin` | Load raw data into the project | `load(source, **options) -> {port: Artifact}`; `file_extensions`; `supports(source)` |
| `PROCESSING_NODE` | `NodeBase` | Transform data | `input_ports`, `output_ports`, `parameters`; `run(inputs, params) -> {port: Artifact}` |
| `ANNOTATION` | `AnnotationBase` | User annotations on data | `axis_roles()`, `resolve(dataset)`, `to_dict/from_dict` |
| `VISUALIZATION` | `ViewPlugin` | Render an artifact | `supports(artifact) -> bool` (classmethod); `create_widget(artifact, context) -> QWidget`; `priority` |
| `PANEL` | `PanelPlugin` | Dockable tool panel | `create_widget(context) -> QWidget`; `default_area`; `default_visible` |
| `EXPORTER` | *(none yet)* | Export artifacts/projects | Enum exists; no contract yet |

## Step-by-step: implement a new data source

1. Subclass `DataSourcePlugin`.
2. Implement `load()`.
3. Decide the output port name — the conventional value for a single-output
   source is `"out"` (the `ExecutionEngine.SOURCE_PORT`).
4. Build a `Dataset` (+ `AxisMeta` via `set_axis_role`) and wrap it in an
   `Artifact`; return `{"<port>": artifact}`.
5. Implement `supports()` (or rely on `file_extensions`).
6. Register and add to your plugin package's `__init__`.

Reference implementation: `alchemetra.builtin.csv_source.CsvDataSourcePlugin`.

## Step-by-step: implement a new processing node

1. Subclass `NodeBase`.
2. Declare `input_ports` / `output_ports` as `tuple[PortSpec, ...]`.
3. Declare `parameters` as `tuple[ParameterSpec, ...]`.
4. Implement pure `run()`.
5. Return a mapping of output port → new `Artifact`.

Important:

- Use `Dataset.copy_with(...)` instead of mutating.
- Use `Artifact(...).labelled(...)` for a human-readable label.
- `validate_params` / `validate_inputs` are called by the engine — keep
  your overrides consistent with the base behaviour.

Reference implementation: `alchemetra.builtin.example_nodes.ScaleNode`.

## Step-by-step: implement a new annotation

Subclass `AnnotationBase` (a dataclass). Geometry is expressed in terms of
`AxisRole`s, never dimension names:

- `axis_roles()` → tuple of roles the annotation is defined against.
- `resolve(dataset)` → maps roles → concrete dimension names (raises
  `ValueError` if impossible).

Serialization: `to_dict()` / `from_dict()` must round-trip through the
project file. Built-ins: peak, ROI, separator.

## Step-by-step: implement a new view

Subclass `ViewPlugin`:

- Implement `supports(artifact) -> bool` as a **classmethod**; typically
  inspect `artifact.dataset.axes_with_role(...)` / `dims` rather than
  dimension names.
- Implement `create_widget(artifact, context) -> QWidget`.
- Set `priority` to resolve conflicts (higher wins; main window picks the
  best supporter).

Built-in views: spectrum (`core.view.spectrum`), heatmap
(`core.view.heatmap`), table (`core.view.table`).

## Step-by-step: implement a new panel

Subclass `PanelPlugin`; implement `create_widget(context) -> QWidget`; set
`default_area` / `default_visible`.

## Versioning & stability

- `plugin_id` must be treated as a stable identifier (used in templates and
  project files). Never rename or reuse ids.
- Bump `version` when changing behaviour that affects saved templates.
- `WorkflowGraph.TEMPLATE_VERSION` is currently `1`; migrations for older
  templates go into `WorkflowGraph.from_template`.

## Third-party plugin packages

Because discovery today is *programmatic* (import + `@register_plugin`),
third-party plugins are distributed as normal Python packages that expose
their plugin classes. A future evolution is entry-point based discovery
(`importlib.metadata.entry_points`), which the registry docstring already
anticipates.

Recommended package layout for a third-party plugin:

```
myplugin/
├── pyproject.toml
└── src/
    └── myplugin/
        ├── __init__.py          # imports plugin modules (registers them)
        ├── plugins/
        │   ├── __init__.py
        │   └── csv_source.py    # @register_plugin subclass
        └── ...
```

## Testing your plugin

- Register/unregister in tests via imports or `register_all()`.
- Keep plugin tests headless: set `QT_QPA_PLATFORM=offscreen` for UI plugins.
- Use `tmp_path` for file-based data sources.
- For nodes: build `Artifact`/`Dataset` fixtures and exercise
  `ExecutionEngine` end to end (see `tests/test_smoke.py`).

## Example: default CSV plugin in 60 lines of intent

The shipped sample (`core.source.csv` → `core.view.table`) demonstrates the
complete loop:

1. `CsvDataSourcePlugin.load()` turns a header-driven CSV into a
   `Dataset` (row axis + one variable per column).
2. The artifact is placed in a workflow as an entry node.
3. `TableView.supports()` claims tabular artifacts.
4. The table view renders rows × columns.
5. `ProjectManager.save()` writes `project.json` + zarr store;
   `ProjectManager.load()` restores the artifact (data + axis metadata).

See `tests/test_csv_plugin.py` for the reference test coverage of this loop.
