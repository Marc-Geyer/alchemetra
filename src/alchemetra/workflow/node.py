from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True)
class WorkflowNode:

    name: str

    id: str = field(default_factory=lambda: str(uuid4()))

    settings: dict = field(default_factory=dict)

"""
    Later implementations:
     - ImportNode
     - PeakDetectionNode
     - ROISelectionNode
     - ExportNode
"""