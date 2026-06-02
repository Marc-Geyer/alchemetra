class AnnotationService:

    def __init__(self):

        self._annotations = []

    def add(self, annotation):

        self._annotations.append(annotation)

    def remove(self, annotation_id):
        self._annotations.remove(annotation_id)