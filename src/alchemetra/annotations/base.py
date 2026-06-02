from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True)
class Annotation:

    dataset_id: str

    id: str = field(default_factory=lambda: str(uuid4()))

    label: str = ""