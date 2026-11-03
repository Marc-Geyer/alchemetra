"""ParameterForm: an editor form generated from a node's ParameterSpecs.

Plugin authors get a parameter UI for free by declaring ``parameters`` on
their NodeBase subclass; they can also reuse this widget in their own panels.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from ...workflow.node import ParameterSpec

_INT_MAX = 2_147_483_647


class ParameterForm(QWidget):
    """Emits :attr:`values_changed` with the complete value dict on any edit."""

    values_changed = Signal(dict)

    def __init__(
        self,
        specs: Iterable[ParameterSpec],
        values: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        values = values or {}
        self._getters: dict[str, Callable[[], Any]] = {}
        layout = QFormLayout(self)
        for spec in specs:
            value = values.get(spec.name, spec.default)
            editor, getter = self._make_editor(spec, value)
            self._getters[spec.name] = getter
            layout.addRow(spec.label or spec.name, editor)

    def values(self) -> dict[str, Any]:
        return {name: getter() for name, getter in self._getters.items()}

    def _emit(self, *_args) -> None:
        self.values_changed.emit(self.values())

    def _make_editor(self, spec: ParameterSpec, value: Any):
        if spec.kind == "float":
            w = QDoubleSpinBox()
            w.setDecimals(6)
            w.setRange(-1e12 if spec.min_value is None else spec.min_value, 1e12 if spec.max_value is None else spec.max_value)
            w.setSingleStep(0.1)
            w.setKeyboardTracking(False)
            w.setValue(float(value if value is not None else 0.0))
            w.valueChanged.connect(self._emit)
            return w, w.value
        if spec.kind == "int":
            w = QSpinBox()
            w.setRange(-_INT_MAX if spec.min_value is None else int(spec.min_value), _INT_MAX if spec.max_value is None else int(spec.max_value))
            w.setKeyboardTracking(False)
            w.setValue(int(value if value is not None else 0))
            w.valueChanged.connect(self._emit)
            return w, w.value
        if spec.kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(value))
            w.toggled.connect(self._emit)
            return w, w.isChecked
        if spec.kind == "choice":
            w = QComboBox()
            for choice in spec.choices or ():
                w.addItem(str(choice), choice)
            w.setCurrentIndex(max(0, w.findData(value)))
            w.currentIndexChanged.connect(self._emit)
            return w, w.currentData
        w = QLineEdit("" if value is None else str(value))   # "str" and unknown kinds
        w.editingFinished.connect(self._emit)
        return w, w.text
