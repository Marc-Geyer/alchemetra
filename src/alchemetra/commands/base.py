"""Command pattern base classes for undoable user actions.

Every user-facing edit that should be undoable (adding a node, changing a
parameter, creating an annotation, ...) is expressed as a
:class:`Command`. The :class:`CommandStack` is a simple undo/redo stack;
UI actions push commands onto it instead of mutating state directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Command(ABC):
    """One undoable/redoable user action."""

    #: Short, human-readable description shown in the Edit menu / history
    #: panel, e.g. "Add node 'Baseline correction'".
    description: str = ""

    @abstractmethod
    def execute(self) -> None:
        """Perform the action. Called once, when the command is first
        run."""

    @abstractmethod
    def undo(self) -> None:
        """Reverse the effects of :meth:`execute`."""

    def redo(self) -> None:
        """Re-apply the action after :meth:`undo`. Default: re-execute."""

        self.execute()


class CommandStack:
    """Simple linear undo/redo stack."""

    def __init__(self, max_history: int | None = None) -> None:
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []
        self.max_history = max_history

    def do(self, command: Command) -> None:
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        if self.max_history is not None:
            while len(self._undo_stack) > self.max_history:
                self._undo_stack.pop(0)

    def undo(self) -> None:
        if not self._undo_stack:
            return
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)

    def redo(self) -> None:
        if not self._redo_stack:
            return
        command = self._redo_stack.pop()
        command.redo()
        self._undo_stack.append(command)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)
