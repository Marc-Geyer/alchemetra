from dataclasses import dataclass


@dataclass(slots=True)
class WorkflowEdge:

    source_id: str

    target_id: str