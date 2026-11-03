# API Reference

Complete reference of Alchemetra's public Python API and the plugin
contracts, plus the serialisation formats.

## Entry points

| Entry | Target |
|---|---|
| Console script | `alchemetra = "alchemetra.ui.app:main"` (see `pyproject.toml`) |
| Module | `python -m alchemetra.ui.app` |

## Core API by module

### `alchemetra`

- `alchemetra.__version__` — `"0.1.0"`.

### `alchemetra.plugins`

```python
class PluginKind(Enum):
    DATA_SOURCE = auto()
    PROCESSING_NODE = auto()
    ANNOTATION = auto()
    VISUALIZATION = auto()
    EXPORTER = auto()
    PANEL = auto()


class PluginBase(ABC):
    plugin_id: ClassVar[str]        # stable, never change once shipped
    plugin_kind: ClassVar[PluginKind]
    display_name: ClassVar[str] = ""
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = ""
    @classmethod
    def describe(cls) -> dict[str, Any]: ...


class PluginRegistrationError(Exception):
    ...


class PluginRegistry:
    @classmethod
    def register(cls, plugin_cls: type[PluginBase]) -> type[PluginBase]: ...
    @classmethod
    def unregister(cls, kind: PluginKind, plugin_id: str) -> None: ...
    @classmethod
    def get(cls, kind: PluginKind, plugin_id: str) -> type[PluginBase]: ...
    @classmethod
    def all(cls, kind: PluginKind) -> Iterable[type[PluginBase]]: ...
    @classmethod
    def describe_all(cls, kind: PluginKind) -> list[dict]: ...


def register_plugin(plugin_cls: type[PluginBase]) -> type[PluginBase]:
    """Class decorator: register a plugin with the global registry."""
    ...
```

Notes:
- The registry is process-wide and keyed by `(PluginKind, plugin_id)`.
- Re-registering the *same* class is allowed; registering a *different* class
  under an existing id raises `PluginRegistrationError`.

### `alchemetra.data.dataset`

```python
class AxisRole(Enum):
    GENERIC = auto()
    SPECTRAL = auto()      # e.g. wavenumber, wavelength, m/z
    TEMPORAL = auto()       # acquisition time / elapsed time
    SPATIAL = auto()        # retention time, position, depth, ...
    INTENSITY = auto()      # signal magnitude / counts / absorbance
    POTENTIAL = auto()      # electrochemical potential
    CURRENT = auto()        # electrochemical current
    SAMPLE = auto()         # categorical sample / replicate identifier
    CUSTOM = auto()         # domain-specific role, see AxisMeta.custom_role

@dataclass
class AxisMeta:
    name: str
    role: AxisRole = AxisRole.GENERIC
    unit: str | None = None
    label: str | None = None
    custom_role: str | None = None
    def to_dict(self) -> dict
    @classmethod def from_dict(cls, data) -> AxisMeta

class Dataset:
    def __init__(self, data: xr.Dataset, axis_meta: dict[str, AxisMeta] | None = None, metadata: dict | None = None)
    @property xr -> xr.Dataset          # read-only from outside
    @property dims -> tuple[str, ...]
    def set_axis_meta(self, name, meta) -> None
    def set_axis_role(self, name, role, unit=None, label=None, custom_role=None) -> None
    def get_axis_meta(self, name) -> AxisMeta
    def axes_with_role(self, role, custom_role=None) -> list[str]
    def primary_axis(self, role, custom_role=None) -> str | None
    def axis_meta_dict(self) -> dict[str, dict[str, Any]]
    @classmethod
    def from_xarray(cls, data, axis_meta_dict=None, metadata=None) -> Dataset
    def copy_with(self, data: xr.Dataset) -> Dataset   # carry-over semantics
```

### `alchemetra.data.artifact`

```python
@dataclass
class Artifact:
    dataset: Dataset
    id: str = field(default_factory=lambda: uuid.uuid4().hex)   # stable id
    produced_by: str | None = None
    output_port: str | None = None
    params_hash: str | None = None
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def labelled(self, label: str) -> "Artifact"   # chainable
    @property
    def label(self) -> str                          # metadata["label"] or id[:8]
```

### `alchemetra.data.datasource`

```python
class DataSourcePlugin(PluginBase):
    plugin_kind: ClassVar[PluginKind] = PluginKind.DATA_SOURCE
    file_extensions: ClassVar[tuple[str, ...]] = ()   # used for open-file dispatch

    @abstractmethod
    def load(self, source: Path | str, **options: Any) -> dict[str, Artifact]:
        """Return mapping of output_port -> Artifact."""

    def supports(self, source: Path | str) -> bool:
        """Default extension-based check; override for smarter sniffing."""
```

### `alchemetra.workflow.node`

```python
@dataclass(frozen=True)
class PortSpec:
    name: str
    label: str | None = None
    required_role: AxisRole | None = None   # warn/refuse on wrong axis
    required: bool = True

@dataclass(frozen=True)
class ParameterSpec:
    name: str
    kind: str          # "int" | "float" | "str" | "bool" | "choice" | "axis"
    default: Any = None
    label: str | None = None
    choices: tuple | None = None          # kind == "choice"
    min_value: float | None = None        # int/float kinds
    max_value: float | None = None
    axis_role: AxisRole | None = None     # kind == "axis"

class NodeBase(PluginBase):
    plugin_kind: ClassVar[PluginKind] = PluginKind.PROCESSING_NODE
    input_ports: ClassVar[tuple[PortSpec, ...]] = ()
    output_ports: ClassVar[tuple[PortSpec, ...]] = ()
    parameters: ClassVar[tuple[ParameterSpec, ...]] = ()

    @classmethod
    def default_params(cls) -> dict[str, Any]: ...
    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> dict[str, Any]: ...  # fills defaults, validates
    def validate_inputs(self, inputs: dict[str, Artifact]) -> None: ...  # raises ValueError
    @abstractmethod
    def run(self, inputs: dict[str, Artifact], params: dict[str, Any]) -> dict[str, Artifact]:
        """Pure function. Return {output_port: Artifact}."""
```

### `alchemetra.workflow.graph`

```python
class GraphError(Exception)

@dataclass
class NodeInstance:
    id: str
    plugin_id: str
    params: dict[str, Any] = field(default_factory=dict)
    position: tuple[float, float] = (0.0, 0.0)
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict
    @classmethod
    def from_dict(cls, data: dict) -> NodeInstance

class WorkflowGraph:
    TEMPLATE_VERSION: ClassVar[int] = 1
    def __init__(self) -> None: self.nodes: dict[str, NodeInstance]; self.edges: list[Edge]
    def add_node(self, node: NodeInstance) -> NodeInstance
    def remove_node(self, node_id: str) -> None
    def connect(self, source_node: str, source_port: str, target_node: str, target_port: str) -> Edge
    def disconnect(self, edge: Edge) -> None
    def incoming_edges(self, node_id: str) -> list[Edge]
    def outgoing_edges(self, node_id: str) -> list[Edge]
    def topo_order(self) -> list[str]       # raises GraphError on cycle
    def downstream_of(self, node_id: str) -> set[str]
    def to_template(self) -> dict[str, Any]      # {"template_version", "nodes", "edges"}
    @classmethod
    def from_template(cls, data: dict[str, Any]) -> WorkflowGraph
```

### `alchemetra.workflow.execution`

```python
def _hash_params(params: dict[str, Any]) -> str

@dataclass
class ExecutionResult:
    artifacts: dict[str, Artifact]
    node_outputs: dict[str, dict[str, str]]
    executed_nodes: list[str]

class ExecutionEngine:
    SOURCE_PORT: ClassVar[str] = "out"
    def __init__(self, graph: WorkflowGraph, tracker: ProvenanceTracker | None = None) -> None
    def invalidate(self, node_id: str) -> None
    def run(self, source_artifacts: dict[str, Artifact], target_nodes: list[str] | None = None) -> ExecutionResult
```

### `alchemetra.provenance`

```python
@dataclass(frozen=True)
class LineageRecord:
    node_id: str
    plugin_id: str
    params: dict[str, Any]
    inputs: dict[str, str]     # port name -> artifact id
    outputs: dict[str, str]    # port name -> artifact id
    timestamp: datetime
    def to_dict(self) -> dict
    @classmethod
    def from_dict(cls, data: dict) -> LineageRecord

class ProvenanceTracker:
    def __init__(self) -> None
    def record(self, node_id, plugin_id, params, inputs, outputs) -> LineageRecord
    def producer_of(self, artifact_id: str) -> LineageRecord | None
    def lineage_of(self, artifact_id: str) -> list[LineageRecord]   # oldest first
    def to_dict(self) -> dict
    @classmethod
    def from_dict(cls, data: dict) -> ProvenanceTracker
```

### `alchemetra.project`

```python
@dataclass
class Project:
    name: str = "Untitled project"
    raw_data: dict[str, Artifact]      # entry node id -> Artifact
    derived_data: dict[str, Artifact] # artifact id -> Artifact
    workflow: WorkflowGraph = field(default_factory=WorkflowGraph)
    annotations: list[AnnotationBase]
    results: dict[str, Any]
    provenance: ProvenanceTracker

    def run(self, target_nodes: list[str] | None = None) -> ExecutionResult
    def add_raw_data(self, node_id: str, artifact: Artifact, plugin_id: str = "core.source.imported") -> NodeInstance
    def unique_node_id(self, base: str) -> str
    def add_processing_node(self, plugin_id: str, after: str | None = None, params: dict[str, Any] | None = None) -> NodeInstance
    def remove_node(self, node_id: str) -> None
    def set_node_params(self, node_id: str, params: dict[str, Any]) -> None
    def add_annotation(self, annotation: AnnotationBase) -> None
    def remove_annotation(self, annotation_id: str) -> None
    def annotations_for(self, artifact_id: str) -> list[AnnotationBase]
    def export_template(self) -> dict[str, Any]
    def import_template(self, template: dict[str, Any]) -> None

class ProjectManager:
    PROJECT_METADATA_FILE: ClassVar[str] = "project.json"
    DATA_DIR: ClassVar[str] = "data"
    @staticmethod
    def save(project: Project, path: Path | str) -> None
    @staticmethod
    def load(path: Path | str) -> Project
    # extension points:
    @staticmethod
    def _write_artifact(artifact: Artifact, data_dir: Path) -> dict[str, Any]
    @staticmethod
    def _read_artifact(meta: dict[str, Any], data_dir: Path) -> Artifact
```

### `alchemetra.commands`

```python
class Command(ABC):
    description: str = ""
    @abstractmethod execute(self) -> None
    @abstractmethod undo(self) -> None
    def redo(self) -> None: ...      # default: re-execute

class CommandStack:
    def __init__(self, max_history: int | None = None) -> None
    def do(self, command: Command) -> None
    def undo(self) -> None
    def redo(self) -> None
    @property can_undo -> bool
    @property can_redo -> bool
```

### `alchemetra.services`

```python
Listener = Callable[[AnnotationBase, str], None]   # (annotation, "added"|"removed")

class AnnotationService:
    def __init__(self, project: Project) -> None
    def add(self, annotation: AnnotationBase) -> AnnotationBase
    def remove(self, annotation_id: str) -> None
    def get(self, annotation_id: str) -> AnnotationBase | None
    def for_artifact(self, artifact_id: str) -> list[AnnotationBase]
    def by_role(self, role: AxisRole) -> list[AnnotationBase]
    def on_change(self, listener: Listener) -> Callable[[], None]   # returns unsubscribe

class ImportService:
    @staticmethod
    def supported_extensions() -> list[str]
    @staticmethod
    def find_plugin(path: str | Path) -> type[DataSourcePlugin] | None
    @staticmethod
    def import_file(project: Project, path: str | Path, **options) -> list[Artifact]
```

### `alchemetra.ui.context`

```python
class UiContext(QObject):
    project_changed = Signal()
    workflow_changed = Signal()
    annotations_changed = Signal(object, str)   # (AnnotationBase, kind)
    artifact_selected = Signal(str)
    view_requested = Signal(str)
    node_selected = Signal(str)                 # workflow node id

    @property project -> Project
    @property annotation_service -> AnnotationService
    def set_project(self, project: Project) -> None
    def artifact(self, artifact_id: str) -> Artifact | None
    def all_artifacts(self) -> dict[str, Artifact]
    def select_artifact(self, artifact_id: str) -> None
    def select_node(self, node_id: str) -> None
    def request_view(self, artifact_id: str) -> None
    def notify_workflow_changed(self) -> None
```

### `alchemetra.ui.main_window`

```python
class MainWindow(QMainWindow):
    def __init__(self, context: UiContext | None = None) -> None
    def reload_panels(self) -> None                       # (re)create docks from registry
    def open_view_for_artifact(self, artifact_id: str) -> None
    def new_project(self) -> None
    def run_workflow(self) -> None
    def import_file(self, path: str | Path, **options) -> None
    def save_project(self, path: str | Path) -> None
    def open_project(self, path: str | Path) -> None
    def export_template(self, path: str | Path) -> None
    def load_template(self, path: str | Path) -> None
```

## Plugin API contracts

### Data source — `DataSourcePlugin`

```python
@register_plugin
class MyDataSource(DataSourcePlugin):
    plugin_id = "core.source.myformat"     # stable; used in templates / project files
    display_name = "My Format"
    description = "..."
    version = "0.1.0"
    file_extensions = ("myext",)           # for open-file dispatch

    def load(self, source: Path | str, **options: Any) -> dict[str, Artifact]:
        # return {output_port: Artifact}
        ...
```

### Processing node — `NodeBase`

```python
@register_plugin
class MyNode(NodeBase):
    plugin_id = "core.processing.my_step"
    display_name = "My Step"
    description = "..."
    version = "0.1.0"
    input_ports = (PortSpec(name="in", label="Input", required=True, required_role=AxisRole.SPECTRAL),)
    output_ports = (PortSpec(name="out", label="Output", required=True),)
    parameters = (
        ParameterSpec(name="factor", kind="float", default=1.0, label="Factor", min_value=0.0, max_value=1e6),
        ParameterSpec(name="mode", kind="choice", default="fast", choices=("fast", "slow"), label="Mode"),
        ParameterSpec(name="axis", kind="axis", default=None, axis_role=AxisRole.SPECTRAL, label="Axis"),
    )

    def run(self, inputs: dict[str, Artifact], params: dict[str, Any]) -> dict[str, Artifact]:
        # pure; returns {output_port: Artifact}
        ...
```

### Annotation — `AnnotationBase`

```python
@dataclass
class AnnotationBase(PluginBase):
    plugin_kind: ClassVar[PluginKind] = PluginKind.ANNOTATION
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    artifact_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def axis_roles(self) -> tuple[AxisRole, ...]: ...

    def resolve(self, dataset: Dataset) -> dict[AxisRole, str]: ...  # role -> dim name

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnnotationBase: ...

# Built-in examples:
#   PeakAnnotation      plugin_id="core.annotation.peak"      (position, width)
#   ROIAnnotation        plugin_id="core.annotation.roi"        (bounds: {AxisRole: (min, max)})
#   SeparatorAnnotation plugin_id="core.annotation.separator" (position, axis_role)
```

### View — `ViewPlugin`

```python
class ViewPlugin(PluginBase):
    plugin_kind: ClassVar[PluginKind] = PluginKind.VISUALIZATION
    priority: ClassVar[int] = 0        # higher wins when several match

    @classmethod
    def supports(cls, artifact: Artifact) -> bool: ...   # pick best via priority

    def create_widget(self, artifact: Artifact, context: UiContext) -> QWidget: ...
```

### Panel — `PanelPlugin`

```python
class PanelPlugin(PluginBase):
    plugin_kind: ClassVar[PluginKind] = PluginKind.PANEL
    default_area: ClassVar[Qt.DockWidgetArea] = Qt.DockWidgetArea.LeftDockWidgetArea
    default_visible: ClassVar[bool] = True

    def create_widget(self, context: UiContext) -> QWidget: ...
```

### Exporter — `EXPORTER`

Declared in `PluginKind`, but no base class/contract exists yet. Planned:
a plugin kind that turns an artifact (or project) into a shareable file
(e.g. figures, reports). Until then, export is done via
`Project.export_template()` and manual artifact handling.

## Serialisation formats

### Processing template (workflow)

`WorkflowGraph.to_template()` produces:

```json
{
  "template_version": 1,
  "nodes": [
    {
      "id": "...",
      "plugin_id": "core.example.scale",
      "params": {"factor": 2.0},
      "position": [0.0, 0.0],
      "metadata": {}
    }
  ],
  "edges": [
    {"source_node": "...", "source_port": "out", "target_node": "...", "target_port": "in"}
  ]
}
```

### Project file (directory)

```
<project-path>/
├── project.json        # manifest (name, raw_data, derived_data, workflow, annotations, results, provenance)
└── data/
    └── <artifact_id>.zarr   # xarray/zarr dataset written by ProjectManager._write_artifact
```

`project.json` keys:

| Key | Content |
|---|---|
| `name` | Project name |
| `raw_data` | Mapping entry-node-id → artifact metadata (see below) |
| `derived_data` | Mapping artifact-id → artifact metadata |
| `workflow` | Workflow template (as above) |
| `annotations` | List of annotation dicts (each carries its `plugin_id`) |
| `results` | Free-form user results |
| `provenance` | `{"records": [...]}` provenance log |

Artifact metadata written by `ProjectManager._write_artifact`:

```json
{
  "id": "<artifact id>",
  "store": "<artifact id>.zarr",
  "produced_by": "..." | null,
  "output_port": "out" | null,
  "params_hash": "..." | null,
  "created_at": "ISO-8601",
  "metadata": {},
  "axis_meta": {"<axis>": {"name": "...", "role": "...", "unit": "...", "label": "...", "custom_role": "..."}}
}
```

### Error types

| Exception | Raised by |
|---|---|
| `PluginRegistrationError` | `PluginRegistry.register` (duplicate id) |
| `KeyError` | `PluginRegistry.get` (unknown plugin id/kind) |
| `GraphError` | workflow graph validation (cycles, unknown nodes) |
| `ValueError` | parameter validation, input validation, CSV parsing, annotation resolve |

## Adding a capability? Start here

- New data source → `DataSourcePlugin` subclass + register.
- New transformation → `NodeBase` subclass + register; declare ports/params.
- New user annotation → `AnnotationBase` subclass + register.
- New visualisation → `ViewPlugin` subclass + register + `supports`.
- New tool dock → `PanelPlugin` subclass + register.
- New export → future `EXPORTER` kind (until then: manual artefact handling).
