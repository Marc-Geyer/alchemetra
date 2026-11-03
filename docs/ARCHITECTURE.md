# Architecture

This document describes Alchemetra's layered architecture, module map,
data flow and design principles.

## Layered overview

```
┌──────────────────────────────────────────────────────────────┐
│  Application layer                                           │
│  alchemetra.ui.app  →  alchemetra.ui.main_window  (Qt shell) │
│                                                              │
│  Built-in UI plugins:                                        │
│   • Panels  : project explorer, properties, workflow,      │
│               node inspector                                  │
│   • Views   : spectrum, heatmap, table                       │
├──────────────────────────────────────────────────────────────┤
│  Plugin layer (contracts)                                    │
│  alchemetra.plugins (PluginBase, PluginKind, registry)       │
│  alchemetra.data (DataSourcePlugin)                          │
│  alchemetra.workflow (NodeBase, PortSpec, ParameterSpec)     │
│  alchemetra.annotations (AnnotationBase)                     │
│  alchemetra.ui.panels / views (PanelPlugin, ViewPlugin)      │
├──────────────────────────────────────────────────────────────┤
│  Core domain layer                                           │
│  alchemetra.data   (Dataset, Artifact)                       │
│  alchemetra.workflow (graph, execution)                      │
│  alchemetra.provenance (tracker, lineage)                    │
│  alchemetra.annotations (base + built-in types)              │
│  alchemetra.project (Project, ProjectManager)                │
│  alchemetra.commands (undo/redo)                             │
│  alchemetra.services (AnnotationService, ImportService)     │
└──────────────────────────────────────────────────────────────┘
```

### Layer responsibilities

1. **Application layer** (`alchemetra.ui.*`) — Qt widgets only. Owns the
   main window, dock widgets, tabs, menus, and wires `UiContext` signals to
   UI actions. Contains **no domain logic**.
2. **Plugin layer** (`alchemetra.plugins.*`, plugin base classes) — pure
   Python contracts. Nothing here knows about Qt (except where noted).
3. **Core domain layer** (`alchemetra.<domain>.*`) — data model, workflow,
   provenance, project, commands, services.

### Dependency direction

```
UI plugins  →  UiContext  →  Project/Services  →  Core
Panels/Views never talk to MainWindow internals; they only use UiContext.
Nodes  →  Artifact/Dataset  →  AxisMeta/AxisRole
Execution engine → NodeBase (via registry) → Artifact/Dataset
ProjectManager → Artifact/Dataset (+ storage extension points)
```

## Module map

### `alchemetra` (core)

| Module | Responsibility |
|---|---|
| `plugins/` | `PluginBase`, `PluginKind`, `PluginRegistry`, `register_plugin`, `PluginRegistrationError` |
| `data/` | `Dataset`, `Artifact`, `DataSourcePlugin` |
| `workflow/` | `graph.py` (`WorkflowGraph`, `NodeInstance`, `Edge`), `node.py` (`NodeBase`, `PortSpec`, `ParameterSpec`), `edge.py`, `execution.py` (`ExecutionEngine`) |
| `provenance/` | `tracker.py` (`ProvenanceTracker`), `lineage.py` (`LineageRecord`) |
| `annotations/` | `base.py` (`AnnotationBase`), `peak.py`, `roi.py`, `separator.py` |
| `project/` | `project.py` (`Project`), `project_manager.py` (`ProjectManager`) |
| `commands/` | `base.py` (`Command`, `CommandStack`) |
| `services/` | `annotation_service.py` (`AnnotationService`), `import_service.py` (`ImportService`) |

### `alchemetra.builtin` (built-in default plugins)

- `csv_source.py` — `CsvDataSourcePlugin` (`DATA_SOURCE`, id
  `core.source.csv`): delimited text import (spectrum / series / table)
- `example_nodes.py` — `ScaleNode` (`PROCESSING_NODE`, id `core.example.scale`)
- `processing_nodes.py` — `CropNode`, `NormalizeNode`, `SmoothNode`
  (`PROCESSING_NODE`, ids `core.node.crop`, `core.node.normalize`,
  `core.node.smooth`)

### `alchemetra.ui.builtin` (built-in UI plugins) — populated by `register_all()`

- Panels: `core.panel.project_explorer`, `core.panel.properties`,
  `core.panel.workflow`, `core.panel.node_inspector`
- Views: `core.view.spectrum`, `core.view.heatmap`, `core.view.table`

### `alchemetra.ui` (Qt shell)

- `app.py` — entry (`main()`)
- `context.py` — `UiContext` (signals + current project)
- `main_window.py` — `MainWindow` (menus, panels, views, actions)
- `panels/base.py` — `PanelPlugin`
- `views/base.py` — `ViewPlugin`
- `panels/`, `views/` (builtin implementations)
- `widgets/parameter_form.py` — `ParameterForm` (UI from `ParameterSpec`s)

## Data flow

```
CSV file
  │  DataSourcePlugin.load(source) → {output_port: Artifact}
  ▼
Artifact (dataset + provenance fields)
  │  ExecutionEngine.run(source_artifacts={entry_node_id: artifact})
  │      → nodes resolve plugin_id via PluginRegistry(PROCESSING_NODE)
  │      → inputs gathered from upstream edges
  │      → NodeBase.run (pure) → new Artifacts
  │      → cache + ProvenanceTracker.record
  ▼
ExecutionResult (artifacts, node_outputs, executed_nodes)
  │  Project.derived_data.update(result.artifacts)
  ▼
ViewPlugin (MainWindow.open_view_for_artifact)
  │  ViewPlugin.supports(artifact) → best by priority
  ▼
QWidget displayed in tab
```

## Design principles in detail

### Axis semantics

`Dataset` wraps an `xarray.Dataset` and attaches `AxisMeta` entries keyed by
dimension / coordinate / variable name. `AxisRole` enumerates semantic roles
(`SPECTRAL`, `TEMPORAL`, `SPATIAL`, `INTENSITY`, `POTENTIAL`, `CURRENT`,
`SAMPLE`, `CUSTOM`). Nodes and views use `axes_with_role()` / `primary_axis()`
instead of hardcoding names such as `"wavenumber"`.

### Immutability

Artifacts are immutable from the outside. Processing nodes must return new
`Artifact` instances (via `Dataset.copy_with`) and never mutate inputs, so
inputs stay valid for caching and undo.

### Purity

`NodeBase.run(inputs, params) -> dict[str, Artifact]` must be pure:
same inputs + params → same outputs. This is required for execution caching
(`cache_key = node_id + params_hash + input artifact ids`) and deterministic
replay of saved templates.

### Provenance

`ProvenanceTracker` keeps an append-only `LineageRecord` log with inputs and
outputs artifact ids; `lineage_of(artifact_id)` walks the chain backwards.

### Serialisation

- Workflow: `WorkflowGraph.to_template()` / `from_template()` — JSON-friendly
  dict, `template_version` field.
- Project: `ProjectManager.save()/load()` — directory containing
  `project.json` + `data/<artifact_id>.zarr`.
- Annotations: `AnnotationBase.to_dict()` / `from_dict()` via the plugin id.

## Extension points map

| Extension point | Base class | Kind | Registration |
|---|---|---|---|
| Data source | `DataSourcePlugin` | `DATA_SOURCE` | `@register_plugin` |
| Processing node | `NodeBase` | `PROCESSING_NODE` | `@register_plugin` |
| Annotation | `AnnotationBase` | `ANNOTATION` | `@register_plugin` |
| Visualization | `ViewPlugin` | `VISUALIZATION` | `@register_plugin` |
| Panel | `PanelPlugin` | `PANEL` | `@register_plugin` |
| Exporter | — (planned) | `EXPORTER` | `@register_plugin` (enum exists) |

Each extension point is described in [API.md](API.md) and
[PLUGIN_DEVELOPMENT.md](PLUGIN_DEVELOPMENT.md).
