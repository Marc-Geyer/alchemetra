from dataclasses import dataclass

from src.alchemetra.annotations.base import Annotation


@dataclass(slots=True)
class ROIAnnotation(Annotation):

    x_min: float = 0
    x_max: float = 0

    y_min: float = 0
    y_max: float = 0