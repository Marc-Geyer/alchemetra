"""Artifacts: the unit of data that flows between workflow nodes.

An :class:`Artifact` bundles a :class:`Dataset` with the bookkeeping
needed to make every analysis reproducible: which node (and parameters)
produced it, when, and from which inputs. Artifacts are immutable from
the outside - a processing node consumes artifacts and produces *new*
ones, it never edits an artifact in place.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .dataset import Dataset


@dataclass
class Artifact:
    """A piece of data with provenance, flowing along a workflow edge."""

    dataset: Dataset

    #: Stable identifier, used to refer to this artifact from the
    #: provenance tracker and from the UI (e.g. "send to new view").
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    #: Node id that produced this artifact, or ``None`` for raw/imported
    #: data that entered the project via a data source (no producing
    #: node in the workflow graph).
    produced_by: str | None = None

    #: Output port name on the producing node (a node can have several
    #: outputs, e.g. "filtered" and "rejected").
    output_port: str | None = None

    #: Hash of the parameters used to produce this artifact - used by the
    #: execution engine for caching/invalidation.
    params_hash: str | None = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    #: Free-form bag for anything plugin authors want to stash, e.g. a
    #: human readable label shown in the UI.
    metadata: dict[str, Any] = field(default_factory=dict)

    def labelled(self, label: str) -> "Artifact":
        """Set a display label and return ``self`` (for chaining)."""

        self.metadata["label"] = label
        return self

    @property
    def label(self) -> str:
        """Human-readable label of this artifact (defaults to a short id)."""

        return self.metadata.get("label", self.id[:8])
