from dataclasses import dataclass, field

from src.alchemetra.annotations.base import Annotation
from src.alchemetra.data.artifact import Artifact
from src.alchemetra.data.dataset import Dataset
from src.alchemetra.workflow.graph import WorkflowGraph


@dataclass
class Project:

    name: str

    datasets: list[Dataset] = field(default_factory=list)

    artifacts: list[Artifact] = field(default_factory=list)

    annotations: list[Annotation] = field(default_factory=list)

    workflow: WorkflowGraph = field(
        default_factory=WorkflowGraph
    )