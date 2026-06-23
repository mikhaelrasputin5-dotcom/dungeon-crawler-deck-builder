from pygame import Rect, draw, Color, math
from config import TS

class Tile:
    def __init__(self, x, y, col, walkable=True):
        self.x = x
        self.y = y
        self.rect = Rect(x * TS, y * TS, TS, TS)
        self.col = col
        self.walkable = walkable
        self.typ = 'floor' if walkable else 'wall'

    def update(self):
        pass

    def on_enter(self, g, c):
        pass

    def get_type(self):
        return self.typ

    def get_pos(self):
        return (self.x, self.y)
    
    def draw(self, surf, ofs=(0, 0)):
        r = Rect(self.x * TS + ofs[0], self.y * TS + ofs[1], TS, TS)
        draw.rect(surf, self.col, r)

class WallTile(Tile):
    def __init__(self, x, y):
        super().__init__(x, y, (200, 200, 200), False)

class CrumblingTile(Tile):
    def __init__(self, x, y):
        super().__init__(x, y, (200, 100, 50))
        self.tmr = 300
        self.is_dead = False

    def update(self):
        self.tmr -= 1
        if self.tmr <= 0:
            self.is_dead = True

class SlowTile(Tile):
    def __init__(self, x, y):
        super().__init__(x, y, (100, 100, 255))

class HiddenTile(Tile):
    def __init__(self, x, y):
        super().__init__(x, y, (50, 50, 50))
    
    def draw(self, surf, p_pos):
        d = math.Vector2(self.rect.center).distance_to(p_pos)
        if d < TS * 3:
            draw.rect(surf, (255, 255, 200), self.rect)
        else:
            draw.rect(surf, (20, 20, 20), self.rect)
