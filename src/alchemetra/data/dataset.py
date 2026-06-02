from dataclasses import dataclass, field
from uuid import uuid4
from pathlib import Path


@dataclass(slots=True)
class Dataset:

    name: str
    source_file: Path

    id: str = field(default_factory=lambda: str(uuid4()))

    metadata: dict = field(default_factory=dict)

    parent_id: str | None = None