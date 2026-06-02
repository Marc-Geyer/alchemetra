from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True)
class Artifact:

    name: str

    source_dataset_id: str

    id: str = field(default_factory=lambda: str(uuid4()))

    metadata: dict = field(default_factory=dict)

"""
    Later implementations:
     - PeakTable
     - FitResult
     - ClusterResult
     - ExportResult
"""