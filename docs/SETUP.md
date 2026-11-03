# Setup

## Prerequisites

- Python **>= 3.11**
- A Qt platform plugin (PySide6 ships the `offscreen` platform for headless use; real platforms for GUI use)

## Installation

From source (recommended during development):

```bash
git clone <repo>
cd Alchemetra
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"      # or: pip install -r requirements.txt
```

Dependencies (see `pyproject.toml` / `requirements.txt`):

- `PySide6>=6.6` — Qt bindings (GUI)
- `pyqtgraph>=0.13` — fast plotting
- `xarray>=2024.1` — labelled multi-dimensional arrays
- `numpy`, `scipy`, `h5py`, `zarr` — scientific stack

## Running

```bash
# console script
alchemetra

# module entry
python -m alchemetra.ui.app
```

Headless / CI usage:

```bash
export QT_QPA_PLATFORM=offscreen
python -m alchemetra.ui.app
```

## Tests

```bash
pip install pytest
PYTHONPATH=src python -m pytest tests
# or, if the package is installed:
pytest
```

The UI smoke tests run with the Qt `offscreen` platform.

## Packaging notes

- Package name: `alchemetra`, version `0.1.0`.
- Console script: `alchemetra = "alchemetra.ui.app:main"`.
- Source layout: `src/` layout with setuptools package discovery
  (`[tool.setuptools.packages.find] where = ["src"]`).
- Optional dependency group: `dev = ["pytest"]`.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Qt platform errors | Set `QT_QPA_PLATFORM=offscreen` for headless runs |
| `ModuleNotFoundError: alchemetra` | Run with `PYTHONPATH=src` or install the package |
| zarr warnings on save/load | zarr v3 consolidated-metadata notice; harmless for v2-created stores |
| `PluginRegistrationError` on startup | Duplicate plugin id registered (e.g. plugin imported twice under different module paths) |
| Workflow fails at runtime | Check node `input_ports`/`required_role` wiring; `GraphError` for cycles |

## Next steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for the design.
- Read [API.md](API.md) for the full API.
- Read [PLUGIN_DEVELOPMENT.md](PLUGIN_DEVELOPMENT.md) to extend the platform.
