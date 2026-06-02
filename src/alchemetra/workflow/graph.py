from dataclasses import dataclass, field

from src.alchemetra.workflow.edge import WorkflowEdge
from src.alchemetra.workflow.node import WorkflowNode


@dataclass(slots=True)
class WorkflowGraph:

    nodes: list[WorkflowNode] = field(default_factory=list)

    edges: list[WorkflowEdge] = field(default_factory=list)