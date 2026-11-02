"""Project persistence: saving/loading complete project files.

A project file is a directory containing:

* raw numeric data, intended to be stored with :mod:`zarr` (chunked,
  lazy-loadable - a good fit for large datasets)
* a JSON manifest with the workflow template, annotations, provenance and
  project-level metadata

This module sketches the on-disk layout. Concrete (de)serialisation of
:class:`Dataset`/:class:`Artifact` objects to zarr groups is left as an
extension point (:meth:`ProjectManager._write_artifact` /
:meth:`ProjectManager._read_artifact`) so storage backends can be swapped
later (e.g. HDF5 via h5py) without touching the rest of the application.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import xarray as xr

from ..annotations.base import AnnotationBase
from ..annotations.peak import PeakAnnotation
from ..annotations.roi import ROIAnnotation
from ..annotations.separator import SeparatorAnnotation
from ..data.artifact import Artifact
from ..data.dataset import Dataset
from ..provenance.tracker import ProvenanceTracker
from ..workflow.graph import WorkflowGraph
from .project import Project

#: Registry of built-in annotation classes by plugin_id, used for
#: deserialisation. Once third-party annotation plugins are registered
#: with :class:`~alchemetra.plugins.registry.PluginRegistry`, this should
#: be replaced by a registry lookup
#: (``PluginRegistry.get(PluginKind.ANNOTATION, plugin_id)``).
_ANNOTATION_TYPES: dict[str, type[AnnotationBase]] = {
    PeakAnnotation.plugin_id: PeakAnnotation,
    ROIAnnotation.plugin_id: ROIAnnotation,
    SeparatorAnnotation.plugin_id: SeparatorAnnotation,
}

PROJECT_METADATA_FILE = "project.json"
DATA_DIR = "data"


class ProjectManager:
    """Reads and writes :class:`Project` instances to disk."""

    @staticmethod
    def save(project: Project, path: Path | str) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        data_dir = path / DATA_DIR
        data_dir.mkdir(exist_ok=True)

        raw_data_meta = {
            node_id: ProjectManager._write_artifact(artifact, data_dir)
            for node_id, artifact in project.raw_data.items()
        }
        derived_meta = {
            artifact_id: ProjectManager._write_artifact(artifact, data_dir)
            for artifact_id, artifact in project.derived_data.items()
        }

        manifest: dict[str, Any] = {
            "name": project.name,
            "raw_data": raw_data_meta,
            "derived_data": derived_meta,
            "workflow": project.workflow.to_template(),
            "annotations": [a.to_dict() for a in project.annotations],
            "results": project.results,
            "provenance": project.provenance.to_dict(),
        }

        with open(path / PROJECT_METADATA_FILE, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, default=str)

    @staticmethod
    def load(path: Path | str) -> Project:
        path = Path(path)
        with open(path / PROJECT_METADATA_FILE, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)

        data_dir = path / DATA_DIR

        project = Project(name=manifest.get("name", "Untitled project"))

        for node_id, meta in manifest.get("raw_data", {}).items():
            project.raw_data[node_id] = ProjectManager._read_artifact(meta, data_dir)

        for artifact_id, meta in manifest.get("derived_data", {}).items():
            project.derived_data[artifact_id] = ProjectManager._read_artifact(
                meta, data_dir
            )

        project.workflow = WorkflowGraph.from_template(manifest["workflow"])

        for annotation_data in manifest.get("annotations", []):
            annotation_cls = _ANNOTATION_TYPES.get(annotation_data["plugin_id"])
            if annotation_cls is not None:
                project.annotations.append(annotation_cls.from_dict(annotation_data))

        project.results = manifest.get("results", {})
        project.provenance = ProvenanceTracker.from_dict(
            manifest.get("provenance", {"records": []})
        )

        return project

    # ------------------------------------------------------------------
    # Extension points: dataset <-> on-disk storage
    # ------------------------------------------------------------------
    @staticmethod
    def _write_artifact(artifact: Artifact, data_dir: Path) -> dict[str, Any]:
        """Persist one artifact's :class:`Dataset` to ``data_dir`` and
        return a small metadata dict referencing it.

        TODO: write ``artifact.dataset.xr`` to a zarr group named after
        ``artifact.id`` (e.g. via ``xr.Dataset.to_zarr``), alongside
        ``artifact.dataset.axis_meta_dict()``.
        """

        store_path = f"{artifact.id}.zarr"
        # artifact.dataset.xr.to_zarr(data_dir / store_path, mode="w")
        return {
            "id": artifact.id,
            "store": store_path,
            "produced_by": artifact.produced_by,
            "output_port": artifact.output_port,
            "params_hash": artifact.params_hash,
            "created_at": artifact.created_at.isoformat(),
            "metadata": artifact.metadata,
            "axis_meta": artifact.dataset.axis_meta_dict(),
        }

    @staticmethod
    def _read_artifact(meta: dict[str, Any], data_dir: Path) -> Artifact:
        """Inverse of :meth:`_write_artifact`.

        TODO: load ``data_dir / meta['store']`` via ``xr.open_zarr`` and
        wrap it with :meth:`Dataset.from_xarray` using
        ``meta['axis_meta']``.
        """

        # xr_data = xr.open_zarr(data_dir / meta["store"])
        xr_data = xr.Dataset()
        dataset = Dataset.from_xarray(xr_data, axis_meta_dict=meta.get("axis_meta"))

        return Artifact(
            dataset=dataset,
            id=meta["id"],
            produced_by=meta.get("produced_by"),
            output_port=meta.get("output_port"),
            params_hash=meta.get("params_hash"),
            created_at=datetime.fromisoformat(meta["created_at"]),
            metadata=meta.get("metadata", {}),
        )
