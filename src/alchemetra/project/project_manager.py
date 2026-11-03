"""Save/load a Project to/from a directory (JSON manifest + zarr arrays).

A project file is a directory containing:

* raw numeric data, intended to be stored with :mod:`zarr` (chunked,
  lazy-loadable - a good fit for large datasets)
* a JSON manifest with the workflow template, annotations, provenance and
  project-level metadata

This module implements the on-disk layout together with the storage
backend extension points (:meth:`ProjectManager._write_artifact` /
:meth:`ProjectManager._read_artifact`) so storage backends can be swapped
later (e.g. HDF5 via h5py) without touching the rest of the application.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import xarray as xr

from ..annotations.base import AnnotationBase
from ..data.artifact import Artifact
from ..data.dataset import Dataset
from ..provenance.tracker import ProvenanceTracker
from ..plugins.base import PluginKind
from ..plugins.registry import PluginRegistry
from ..workflow.graph import WorkflowGraph
from .project import Project

MANIFEST_VERSION = 2

PROJECT_METADATA_FILE = "project.json"
DATA_DIR = "data"


class ProjectManager:
    """Reads and writes :class:`Project` instances to disk."""

    @staticmethod
    def save(project: Project, path: Path | str) -> None:
        root = Path(path)
        data_dir = root / DATA_DIR
        data_dir.mkdir(parents=True, exist_ok=True)

        raw_data_meta = {
            node_id: ProjectManager._write_artifact(artifact, data_dir)
            for node_id, artifact in project.raw_data.items()
        }
        derived_data_meta = {
            artifact_id: ProjectManager._write_artifact(artifact, data_dir)
            for artifact_id, artifact in project.derived_data.items()
        }

        manifest = {
            "version": MANIFEST_VERSION,
            "name": project.name,
            "raw_data": raw_data_meta,
            "derived_data": derived_data_meta,
            "workflow": project.workflow.to_template(),
            "annotations": [a.to_dict() for a in project.annotations],
            "results": project.results,
            "provenance": project.provenance.to_dict(),
        }
        (root / PROJECT_METADATA_FILE).write_text(json.dumps(manifest, indent=2, default=str))

        # remove arrays of artifacts that are no longer part of the project
        live_ids = {meta["id"] for meta in list(raw_data_meta.values()) + list(derived_data_meta.values())}
        for stale in data_dir.glob("*.zarr"):
            if stale.stem not in live_ids:
                shutil.rmtree(stale, ignore_errors=True)

    @staticmethod
    def load(path: Path | str) -> Project:
        root = Path(path)
        manifest = json.loads((root / PROJECT_METADATA_FILE).read_text())
        data_dir = root / DATA_DIR
        cache: dict[str, Artifact] = {}

        def artifact_for(meta: dict) -> Artifact:
            if meta["id"] not in cache:
                cache[meta["id"]] = ProjectManager._read_artifact(meta, data_dir)
            return cache[meta["id"]]

        project = Project(name=manifest.get("name", "Untitled project"))
        project.raw_data = {
            nid: artifact_for(m) for nid, m in manifest.get("raw_data", {}).items()
        }
        project.derived_data = {
            aid: artifact_for(m) for aid, m in manifest.get("derived_data", {}).items()
        }
        project.workflow = WorkflowGraph.from_template(manifest["workflow"])

        for annotation_data in manifest.get("annotations", []):
            annotation_cls = PluginRegistry.get(
                PluginKind.ANNOTATION, annotation_data["plugin_id"]
            )
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

        The dataset is written as a zarr group named after the artifact id
        (``<artifact.id>.zarr``), which can later be opened with
        :meth:`xarray.Dataset.load_dataset` / ``xr.open_zarr``.
        """

        store_path = f"{artifact.id}.zarr"
        artifact.dataset.xr.to_zarr(str(data_dir / store_path), mode="w", consolidated=False)

        return {
            "id": artifact.id,
            "store": store_path,
            "produced_by": artifact.produced_by,
            "output_port": artifact.output_port,
            "params_hash": artifact.params_hash,
            "created_at": artifact.created_at.isoformat(),
            "metadata": artifact.metadata,
            "dataset_metadata": artifact.dataset.metadata,
            "axis_meta": artifact.dataset.axis_meta_dict(),
        }

    @staticmethod
    def _read_artifact(meta: dict[str, Any], data_dir: Path) -> Artifact:
        """Inverse of :meth:`_write_artifact`.

        Loads the zarr group referenced by ``meta['id']`` and wraps it in a
        :class:`Dataset` using the stored axis metadata.
        """

        with xr.open_zarr(str(data_dir / f"{meta['id']}.zarr"), consolidated=False) as lazy:
            loaded = lazy.load()
        dataset = Dataset.from_xarray(
            loaded, axis_meta_dict=meta.get("axis_meta"), metadata=meta.get("dataset_metadata")
        )
        artifact = Artifact(
            dataset=dataset,
            id=meta["id"],
            produced_by=meta.get("produced_by"),
            output_port=meta.get("output_port"),
            params_hash=meta.get("params_hash"),
            metadata=dict(meta.get("metadata") or {}),
        )
        if meta.get("created_at"):
            artifact.created_at = datetime.fromisoformat(meta["created_at"])
        return artifact
