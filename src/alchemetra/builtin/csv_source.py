"""Built-in delimited-text data source.

The default source accepts CSV/TSV/TXT files and adapts its interpretation
to what the file actually contains:

* **two columns** (header or not) → a 1D *spectrum*: first column = axis,
  second column = intensity;
* **more than two columns without a header** → a *spectra series*: first
  column = spectral axis, remaining columns = intensity traces over time;
* **more than two columns with a header** → a *wide-format table*: rows are
  observations, columns are measured signals (channels).

Every dataset is tagged semantically via
:class:`~alchemetra.data.dataset.AxisRole` (never by hardcoded dimension
names), so downstream processing nodes and views stay domain-agnostic.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import xarray as xr

from ..data.artifact import Artifact
from ..data.datasource import DataSourcePlugin
from ..data.dataset import AxisMeta, AxisRole, Dataset
from ..plugins.base import PluginKind
from ..plugins.registry import register_plugin

#: Dimension name used for the row axis of imported tables.
ROW_AXIS = "index"


def _clean_column_name(name: str, fallback: str) -> str:
    cleaned = re.sub(r"\W", "_", name.strip())
    return cleaned or fallback


def _is_numeric_row(row: list[str]) -> bool:
    try:
        for cell in row:
            float(cell)
    except ValueError:
        return False
    return True


@register_plugin
class CsvDataSourcePlugin(DataSourcePlugin):
    """Import a delimited text file as a :class:`Dataset`.

    The interpretation is auto-detected from the file content:

    * 2 columns  → 1D spectrum (axis, intensity)
    * >2 columns without header → spectra series (axis × time traces)
    * >2 columns with header → wide-format table (observations × signals)
    """

    plugin_id: ClassVar[str] = "core.source.csv"
    display_name: ClassVar[str] = "Delimited Text / CSV"
    description: ClassVar[str] = (
        "Import a delimited text file: 2 columns -> spectrum, >2 columns "
        "(no header) -> spectra series, header + >2 columns -> channel table."
    )
    version: ClassVar[str] = "0.1.0"
    plugin_kind: ClassVar[PluginKind] = PluginKind.DATA_SOURCE
    file_extensions: ClassVar[tuple[str, ...]] = ("csv", "tsv", "txt")

    # ------------------------------------------------------------------
    # DataSourcePlugin contract
    # ------------------------------------------------------------------
    def load(self, source: Path | str, **options: Any) -> dict[str, Artifact]:
        """Load ``source`` and return a ``{"out": Artifact}`` mapping."""

        path = Path(source)
        delimiter = options.get("delimiter") or self._detect_delimiter(path)
        rows = self._read_rows(path, delimiter)
        if not rows:
            raise ValueError(f"CSV source '{path}' contains no data")

        header, matrix = self._split_header(rows)
        if header is not None and not matrix:
            raise ValueError(f"CSV source '{path}' needs a header and data rows")

        n_cols = len(matrix[0]) if matrix else 0
        if n_cols < 2:
            raise ValueError(
                f"CSV source '{path}' needs at least an axis and an intensity column"
            )

        if n_cols == 2:
            return {"out": self._spectrum_artifact(path, matrix, options)}
        if header is not None:
            return {"out": self._table_artifact(path, header, matrix)}
        return {"out": self._series_artifact(path, matrix, options)}

    # ------------------------------------------------------------------
    # Internals: parsing
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_delimiter(path: Path) -> str:
        for line in path.read_text(encoding="utf-8-sig").splitlines()[:5]:
            for candidate in (",", "\t", ";"):
                if candidate in line:
                    return candidate
        return ","

    @staticmethod
    def _read_rows(path: Path, delimiter: str) -> list[list[str]]:
        rows: list[list[str]] = []
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split(delimiter) if delimiter else stripped.split()
            cells = [p.strip() for p in parts if p.strip()]
            if cells:
                rows.append(cells)
        return rows

    @staticmethod
    def _split_header(
        rows: list[list[str]],
    ) -> tuple[list[str] | None, list[list[float]]]:
        """Split ``rows`` into an optional header and a float matrix."""

        header: list[str] | None = None
        start = 1 if rows and not _is_numeric_row(rows[0]) else 0
        if start == 1:
            header = rows[0]

        matrix: list[list[float]] = []
        for row in rows[start:]:
            values: list[float] = []
            for column, cell in zip(header or range(len(row)), row):
                try:
                    values.append(float(cell))
                except ValueError as exc:
                    raise ValueError(
                        f"CSV source: non-numeric value '{cell}' in column "
                        f"'{column}'"
                    ) from exc
            matrix.append(values)
        return header, matrix

    # ------------------------------------------------------------------
    # Artifact builders
    # ------------------------------------------------------------------
    @staticmethod
    def _spectrum_artifact(
        path: Path, matrix: list[list[float]], options: dict[str, Any]
    ) -> Artifact:
        x = np.array([row[0] for row in matrix], dtype=float)
        y = np.array([row[1] for row in matrix], dtype=float)
        x_name = options.get("x_name") or "wavenumber"
        x_unit = options.get("x_unit") or "cm^-1"
        i_unit = options.get("intensity_unit") or "counts"

        xr_ds = xr.Dataset({"intensity": (x_name, y)}, coords={x_name: x})
        dataset = Dataset(xr_ds)
        dataset.set_axis_role(x_name, AxisRole.SPECTRAL, unit=x_unit)
        dataset.set_axis_role("intensity", AxisRole.INTENSITY, unit=i_unit)

        artifact = Artifact(dataset=dataset).labelled(path.stem or path.name)
        artifact.produced_by = None
        artifact.output_port = "out"
        artifact.metadata["source"] = str(path)
        return artifact

    @staticmethod
    def _series_artifact(
        path: Path, matrix: list[list[float]], options: dict[str, Any]
    ) -> Artifact:
        arr = np.array([row[1:] for row in matrix], dtype=float)
        x_name = options.get("x_name") or "wavenumber"
        time_name = "time"

        xr_ds = xr.Dataset(
            {"intensity": ((x_name, time_name), arr)},
            coords={x_name: np.array([row[0] for row in matrix], dtype=float), time_name: np.arange(arr.shape[1], dtype=float)},
        )
        dataset = Dataset(xr_ds)
        dataset.set_axis_role(x_name, AxisRole.SPECTRAL, unit=options.get("x_unit") or "cm^-1")
        dataset.set_axis_role("intensity", AxisRole.INTENSITY, unit=options.get("intensity_unit") or "counts")
        dataset.set_axis_role(time_name, AxisRole.TEMPORAL, label="spectrum index")

        artifact = Artifact(dataset=dataset).labelled(path.stem or path.name)
        artifact.produced_by = None
        artifact.output_port = "out"
        artifact.metadata["source"] = str(path)
        return artifact

    @staticmethod
    def _table_artifact(
        path: Path, header: list[str], matrix: list[list[float]]
    ) -> Artifact:
        n_rows = len(matrix)
        var_names = [_clean_column_name(h, f"column_{i}") for i, h in enumerate(header)]

        arrays: dict[str, Any] = {}
        for var_name, values in zip(var_names, zip(*matrix)):
            arrays[var_name] = (ROW_AXIS, np.asarray(values, dtype=float))

        xr_ds = xr.Dataset(arrays, coords={ROW_AXIS: np.arange(n_rows, dtype=float)})
        dataset = Dataset(xr_ds)
        dataset.set_axis_meta(ROW_AXIS, AxisMeta(name=ROW_AXIS, role=AxisRole.GENERIC))
        for var_name in var_names:
            dataset.set_axis_role(var_name, AxisRole.INTENSITY, label=var_name)

        artifact = Artifact(dataset=dataset).labelled(path.stem or path.name)
        artifact.produced_by = None
        artifact.output_port = "out"
        artifact.metadata["source"] = str(path)
        artifact.metadata["columns"] = list(var_names)
        return artifact
