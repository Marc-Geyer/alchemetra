This is my basic directory layout
```aiignore
alchemetra/

├── pyproject.toml
│
├── src/
│   └── alchemetra/
│
│       ├── builtin/            # built-in default plugins (csv source, nodes, annotations)
│       ├── commands/           # undo/redo command pattern (base)
│       ├── data/               # dataset, artifact, datasource
│       ├── annotations/        # annotation plugins (peak, ROI, separator)
│       ├── workflow/           # graph, node, edge, execution
│       ├── provenance/         # lineage records, tracker
│       ├── plugins/            # plugin base, registry
│       ├── project/            # project, project manager
│       ├── services/           # annotation service, import service
│       ├── ui/                 # Qt shell: app, context, main_window, panels, views, widgets
│       │
│       └── __init__.py
│
└── tests/
```

Base struckture of a Project:
Project
 - Raw Data
 - Derived Data
 - Workflow
 - User Annotations
 - Results

## Documentation

- [docs/README.md](docs/README.md) — documentation index & overview
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — layered design, module map, data flow
- [docs/API.md](docs/API.md) — complete API reference & serialisation formats
- [docs/SETUP.md](docs/SETUP.md) — setup, running, testing, troubleshooting
- [docs/PLUGIN_DEVELOPMENT.md](docs/PLUGIN_DEVELOPMENT.md) — plugin development guide

## Quick start

```bash
pip install -e ".[dev]"
alchemetra          # or: python -m alchemetra.ui.app
pytest              # run tests (requires PYTHONPATH=src or installed package)
```

## Status

The core framework, the built-in plugin set (data source, processing nodes,
annotations, views, panels) and the Qt user interface are implemented and
covered by an automated test suite (headless via Qt's `offscreen` platform).
The architecture is designed to fully support plugin development.
