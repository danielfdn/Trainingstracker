from ENTITIES.set import Set


class Exercise:
    def __init__(self, sets: list[Set], title: str, weighted: bool, id: int = None):
        self.id = id
        self.sets = sets
        self.title = title
        self.weighted = weighted

    def __str__(self):
        return f"{self.id},{self.title}, {self.sets}, {self.weighted}"
