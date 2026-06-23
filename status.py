from effect import Effect

class Status:
    def __init__(self, id: str, name: str, description: str,
                 decays: bool = True,
                 effects: list[Effect] = None):
        self.id = id
        self.name = name
        self.description = description
        self.effects = effects if effects else []
        self.decays = decays
        self.potency = 1
        self.count = 1

    def copy(self):
        return Status(
            self.id,
            self.name,
            self.description,
            self.decays,
            list(self.effects)
        )

    def decay(self) -> bool:
        self.count -= 1
        if self.count <= 0:
            return True
        return False