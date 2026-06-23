from tile import Tile, CrumblingTile, HiddenTile, SlowTile
from config import GRID_WIDTH, GRID_HEIGHT
import random

class Room:
    def __init__(self):
        self.tiles = []
        self.generate_room()

    def generate_room(self):
        self.tiles = []
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if x == 0 or x == GRID_WIDTH-1 or y == 0 or y == GRID_HEIGHT-1:
                    self.tiles.append(Tile(x, y, (50, 50, 50), False))
                else:
                    chance = random.random()
                    match True:
                        case _ if chance < 0.05:
                            self.tiles.append(CrumblingTile(x, y))
                        case _ if chance < 0.10:
                            self.tiles.append(SlowTile(x, y))
                        case _ if chance < 0.15:
                            self.tiles.append(HiddenTile(x, y))
                        case _:
                            self.tiles.append(Tile(x, y, (100, 100, 100)))

    def update(self):
        for t in self.tiles[:]:
            t.update()
            if hasattr(t, 'is_dead') and t.is_dead:
                self.tiles.remove(t)

    def draw(self, surface, player_pos):
        for t in self.tiles:
            if isinstance(t, HiddenTile):
                t.draw(surface, player_pos)
            else:
                t.draw(surface)