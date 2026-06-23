from tile import Tile, CrumblingTile, HiddenTile, SlowTile
from config import GW, GH
import random

class Room:
    def __init__(self):
        self.tiles = []
        self.gen()

    def gen(self):
        self.tiles = []
        for y in range(GH):
            for x in range(GW):
                if x == 0 or x == GW-1 or y == 0 or y == GH-1:
                    self.tiles.append(Tile(x, y, (50, 50, 50), False))
                else:
                    c = random.random()
                    if c < 0.05:
                        self.tiles.append(CrumblingTile(x, y))
                    elif c < 0.10:
                        self.tiles.append(SlowTile(x, y))
                    elif c < 0.15:
                        self.tiles.append(HiddenTile(x, y))
                    else:
                        self.tiles.append(Tile(x, y, (100, 100, 100)))

    def update(self):
        dead = []
        for t in self.tiles[:]:
            t.update()
            if hasattr(t, 'is_dead') and t.is_dead:
                dead.append(t)
        for t in dead:
            self.tiles.remove(t)

    def draw(self, surf, ppos):
        for t in self.tiles:
            if isinstance(t, HiddenTile):
                t.draw(surf, ppos)
            else:
                t.draw(surf)
