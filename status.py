from effect import Effect

class Status:
    def __init__(self, id, nm, desc, decays=True, effects=None):
        self.id = id
        self.name = nm
        self.description = desc
        self.effects = effects if effects else []
        self.decays = decays
        self.potency = 1
        self.count = 1

    def copy(self):
        return Status(self.id, self.name, self.description, self.decays, list(self.effects))

    def decay(self):
        self.count -= 1
        return self.count <= 0
