# Alchemetra — Documentation

**Alchemetra** is a plugin-based platform for scientific data analysis,
visualisation and reproducible processing workflows.

The core application is implemented as a plugin-based platform; the
architecture is designed so that *every* functional capability — data sources,
processing nodes, annotations, views, panels and exporters — is a pluggable
unit.

---

## Documentation index

| Document | Contents |
|---|---|
| [SETUP.md](SETUP.md) | Installation, running, testing, packaging, troubleshooting |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Layered design, module map, data flow, design principles |
| [API.md](API.md) | Complete API reference (core + plugin contracts + file formats) |
| [PLUGIN_DEVELOPMENT.md](PLUGIN_DEVELOPMENT.md) | How to build plugins, conventions, versioning, packaging |

## Quickstart

```bash
# 1. Install from source (see SETUP.md for alternatives)
pip install -e ".[dev]"

# 2. Run the application
alchemetra
# or
python -m alchemetra.ui.app

# 3. Run the test suite
pytest
```

## What the platform does today

The current implementation ships with:

- **Core data model** — `Dataset` (xarray-backed, semantically annotated via
  `AxisRole`/`AxisMeta`), `Artifact` (immutable unit of data flow with
  provenance fields).
- **Plugin registry** — `@register_plugin`, `PluginRegistry`, `PluginKind`.
- **Workflow engine** — DAG graph, topological execution, result caching,
  provenance tracking, processing-template serialisation.
- **Built-in default plugins**:
  - data source: `core.source.csv` (`CsvDataSourcePlugin`) — *import a
    delimited text file (2 columns → spectrum, series, or header-driven
    channel table), view it as a table / spectrum / heatmap, save & reopen
    it as a project file*;
  - processing nodes: `core.example.scale` (`ScaleNode`), `core.node.crop`,
    `core.node.normalize`, `core.node.smooth`;
  - annotations: `core.annotation.peak`, `core.annotation.roi`,
    `core.annotation.separator`;
  - views: `core.view.spectrum`, `core.view.heatmap`, `core.view.table`.
- **UI shell** — main window with dockable panels (project explorer, properties,
  workflow editor, node inspector) and tabbed artifact views, built entirely
  from `PanelPlugin` / `ViewPlugin` contracts, plus a parameter editor
  generated from node `ParameterSpec`s.

## Repository layout

```
alchemetra/
├── docs/                     # this documentation
├── samples/                  # sample data files (e.g. multichannel.csv)
├── src/
│   └── alchemetra/
│       ├── builtin/          # built-in default plugins (data sources, nodes, annotations)
│       ├── commands/         # undo/redo command pattern
│       ├── data/             # Dataset, Artifact, DataSourcePlugin
│       ├── annotations/      # Annotation plugins (peak, ROI, separator)
│       ├── workflow/         # graph, nodes, edges, execution engine
│       ├── provenance/      # lineage records, tracker
│       ├── plugins/          # PluginBase, PluginKind, registry
│       ├── project/          # Project, ProjectManager (save/load)
│       ├── services/         # AnnotationService, ImportService (facades)
│       ├── ui/               # Qt shell: app, context, main_window, panels, views, widgets
│       └── workflow/...      # (see module map above)
└── tests/
```

## Design principles

1. **Axis semantics live in the data layer** — processing nodes and views
   ask `Dataset` for axes by semantic role (`AxisRole`), never by hardcoded
   dimension name.
2. **Plugins own behaviour, core owns contracts** — the application core
   knows nothing about concrete domain plugins until they register.
3. **Immutability** — processing nodes produce new `Artifact`s via
   `Dataset.copy_with`; inputs are never mutated.
4. **Purity & determinism** — `NodeBase.run` must be a pure function of its
   inputs and resolved parameters (this is what makes caching and template
   replay possible).
5. **Provenance** — every execution is recorded; lineage can be traced back
   to the source artifact.
6. **Serialisation safety** — plugin ids, versions and graph structures are
   designed to round-trip through JSON-based templates / project files.

## Status

The platform core, the built-in plugin set (data source, processing nodes,
annotations, views, panels) and the Qt user interface are implemented and
covered by an automated test suite (headless via Qt's `offscreen` platform).

Next steps / extension ideas:

- drag & drop import of data files into the project explorer;
- a graphical (canvas) workflow editor on top of the node/edge model;
- exporter plugins (`EXPORTER` kind) for figures/reports;
- wiring the command stack (`alchemetra.commands`) into the UI actions.

