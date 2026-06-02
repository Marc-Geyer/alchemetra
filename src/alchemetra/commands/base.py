from abc import ABC
from abc import abstractmethod


class Command(ABC):

    @abstractmethod
    def execute(self):
        ...

    @abstractmethod
    def undo(self):
        ...

"""
    Later Implementations:
     - AddPeakCommand
     - DeletePeakCommand
     - CreateROICommand
     - MoveSeparatorCommand
"""