from dataclasses import dataclass


@dataclass(slots=True)
class LineageEntry:

    source_id: str

    target_id: str

    operation: str