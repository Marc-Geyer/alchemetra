from dataclasses import dataclass

from src.alchemetra.annotations.base  import Annotation


@dataclass(slots=True)
class PeakAnnotation(Annotation):

    x: float = 0.0

    y: float = 0.0