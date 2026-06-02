from dataclasses import dataclass

from src.alchemetra.annotations.base import Annotation


@dataclass(slots=True)
class SeparatorAnnotation(Annotation):

    position: float = 0