"""Processing nodes: the building blocks of a workflow graph.

A :class:`NodeBase` subclass describes *one* processing step (e.g.
"baseline correction", "slice selector", "merge by nearest time"). The
base class only fixes the *contract*: declared ports and parameters, and
a pure ``run`` function. Everything about how nodes are wired together,
cached, replayed or edited in the UI is handled outside this class.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from ..data.artifact import Artifact
from ..data.dataset import AxisRole
from ..plugins.base import PluginBase, PluginKind


@dataclass(frozen=True)
class PortSpec:
    """Describes one input or output port of a node."""

    name: str
    label: str | None = None

    #: Optional: if set, the workflow editor and validation logic can
    #: warn/refuse connections to artifacts that don't have an axis with
    #: this role - without the node itself needing to hardcode anything.
    required_role: AxisRole | None = None

    #: Whether this port must be connected for the node to run.
    required: bool = True


@dataclass(frozen=True)
class ParameterSpec:
    """Describes one user-configurable parameter of a node.

    ``kind`` drives which widget the auto-generated parameter panel uses
    (number spinbox, dropdown, axis-role picker, ...). Keeping this
    declarative (instead of building Qt widgets inside the node) is what
    lets nodes run headless - e.g. for batch/template execution from the
    command line.
    """

    name: str
    kind: str = "float"        # "float" | "int" | "str" | "bool" | "choice" | "axis"
    default: Any = None
    label: str | None = None
    choices: tuple[Any, ...] | None = None  # for kind == "choice"
    min_value: float | None = None
    max_value: float | None = None
    #: For kind == "axis": restrict the axis picker to this role.
    axis_role: AxisRole | None = None


class NodeBase(PluginBase):
    """Base class for all processing nodes.

    Subclasses must declare :attr:`input_ports`, :attr:`output_ports`,
    :attr:`parameters` and implement :meth:`run`. ``run`` must be a pure
    function of its arguments: same inputs + params -> same outputs. This
    is what allows the execution engine to cache results and to replay a
    saved template deterministically.
    """

    plugin_kind: ClassVar[PluginKind] = PluginKind.PROCESSING_NODE

    input_ports: ClassVar[tuple[PortSpec, ...]] = ()
    output_ports: ClassVar[tuple[PortSpec, ...]] = ()
    parameters: ClassVar[tuple[ParameterSpec, ...]] = ()

    @classmethod
    def default_params(cls) -> dict[str, Any]:
        return {p.name: p.default for p in cls.parameters}

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> dict[str, Any]:
        """Fill in defaults and do basic range/choice validation.

        Returns a *new* dict; raises ``ValueError`` on invalid input.
        """

        merged = cls.default_params()
        merged.update(params)
        for spec in cls.parameters:
            value = merged[spec.name]
            if spec.kind in ("int", "float"):
                if spec.min_value is not None and value < spec.min_value:
                    raise ValueError(
                        f"{cls.plugin_id}: parameter '{spec.name}' below "
                        f"minimum ({value} < {spec.min_value})"
                    )
                if spec.max_value is not None and value > spec.max_value:
                    raise ValueError(
                        f"{cls.plugin_id}: parameter '{spec.name}' above "
                        f"maximum ({value} > {spec.max_value})"
                    )
            elif spec.kind == "choice" and spec.choices is not None:
                if value not in spec.choices:
                    raise ValueError(
                        f"{cls.plugin_id}: parameter '{spec.name}' must be "
                        f"one of {spec.choices!r}, got {value!r}"
                    )
        return merged

    def validate_inputs(self, inputs: dict[str, Artifact]) -> None:
        for spec in self.input_ports:
            if spec.required and spec.name not in inputs:
                raise ValueError(
                    f"{self.plugin_id}: missing required input "
                    f"'{spec.name}'"
                )
            artifact = inputs.get(spec.name)
            if artifact is not None and spec.required_role is not None:
                if not artifact.dataset.axes_with_role(spec.required_role):
                    raise ValueError(
                        f"{self.plugin_id}: input '{spec.name}' has no "
                        f"axis with role {spec.required_role.name}"
                    )

    @abstractmethod
    def run(
        self, inputs: dict[str, Artifact], params: dict[str, Any]
    ) -> dict[str, Artifact]:
        """Execute this node.

        Parameters
        ----------
        inputs:
            Mapping from input port name to the :class:`Artifact`
            connected to that port. Guaranteed to satisfy
            :attr:`input_ports` after :meth:`validate_inputs` has run.
        params:
            Fully resolved parameter dict (see :meth:`validate_params`).

        Returns
        -------
        dict mapping output port name -> :class:`Artifact`. The execution
        engine fills in ``produced_by``, ``output_port`` and
        ``params_hash``; implementations only need to set ``dataset``
        (and optionally ``metadata``/label).
        """

        raise NotImplementedError
