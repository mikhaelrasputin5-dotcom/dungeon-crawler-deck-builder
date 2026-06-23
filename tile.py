from pygame import Rect, draw, Color, math
from config import TILE_SIZE

class Tile:
    def __init__(self, x: int, y: int, color: Color, walkable: bool = True):
        self.x = x
        self.y = y
        self.rect = Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.color = color
        self.walkable = walkable
        self.type = 'floor' if walkable else 'wall'

    def update(self):
        pass

    def on_enter(self, game, creature):
        pass

    def get_type(self):
        return self.type

    def get_position(self):
        return (self.x, self.y)
    
    def draw(self, surface, offset=(0, 0)):
        rect = Rect(self.x * TILE_SIZE + offset[0], self.y * TILE_SIZE + offset[1], TILE_SIZE, TILE_SIZE)
        draw.rect(surface, self.color, rect)

class WallTile(Tile):
    def __init__(self, x, y):
        super().__init__(x, y, (200, 200, 200), False)
        self.fence = True

class CrumblingTile(Tile):
    def __init__(self, x, y):
        super().__init__(x, y, (200, 100, 50))
        self.timer = 300
        self.is_dead = False

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.is_dead = True

class SlowTile(Tile):
    def __init__(self, x, y):
        super().__init__(x, y, (100, 100, 255))
        self.slow_factor = 0.5

class HiddenTile(Tile):
    def __init__(self, x, y):
        super().__init__(x, y, (50, 50, 50)) # Dark Grey
    
    def draw(self, surface, player_pos):
        dist = math.Vector2(self.rect.center).distance_to(player_pos)
        if dist < TILE_SIZE * 3:
            draw.rect(surface, (255, 255, 200), self.rect)
        else:
            draw.rect(surface, (20, 20, 20), self.rect)