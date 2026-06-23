import random
from typing import Optional, Tuple
from config import GRID_WIDTH, GRID_HEIGHT
from tile import Tile, WallTile, CrumblingTile, HiddenTile, SlowTile

class RoomRect:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.encounter_positions: list[Tuple[int, int]] = []
        self.cleared = False
        self.door_positions: list[Tuple[int, int]] = []
        self.door_tile_snapshot: dict[Tuple[int, int], Tile] = {}

    @property
    def left(self) -> int:
        return self.x

    @property
    def right(self) -> int:
        return self.x + self.width - 1

    @property
    def top(self) -> int:
        return self.y

    @property
    def bottom(self) -> int:
        return self.y + self.height - 1

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def intersects(self, other: 'RoomRect') -> bool:
        return not (
            self.right < other.left - 1 or
            self.left > other.right + 1 or
            self.bottom < other.top - 1 or
            self.top > other.bottom + 1
        )

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x <= self.right and self.top <= y <= self.bottom


class Floor:
    def __init__(self, width: int = GRID_WIDTH, height: int = GRID_HEIGHT, seed: int | None = None):
        self.width = width
        self.height = height
        self.seed = seed if seed is not None else random.randrange(2**31)
        self.rooms: list[RoomRect] = []
        self.start: Tuple[int, int] = (1, 1)
        self.exit: Tuple[int, int] = (width - 2, height - 2)
        self.tiles: list[list[Tile]] = []
        self.generate()

    def generate(self) -> None:
        rnd = random.Random(self.seed)
        self.tiles = [[WallTile(x, y) for x in range(self.width)] for y in range(self.height)]
        self.rooms = []

        room_count = rnd.randint(3, 8)
        attempts = 0
        while len(self.rooms) < room_count and attempts < 60:
            room_width = rnd.randint(5, min(10, self.width - 3))
            room_height = rnd.randint(5, min(8, self.height - 3))
            max_x = max(1, self.width - room_width - 2)
            max_y = max(1, self.height - room_height - 2)
            room_x = rnd.randint(1, max_x)
            room_y = rnd.randint(1, max_y)
            room = RoomRect(room_x, room_y, room_width, room_height)

            if any(room.intersects(existing) for existing in self.rooms):
                attempts += 1
                continue

            self.carve_room(room)
            self.rooms.append(room)
            attempts += 1

        while len(self.rooms) < 3:
            fallback_width = min(8, self.width - 2)
            fallback_height = min(6, self.height - 2)
            placed = False
            for _ in range(10):
                fallback_x = rnd.randint(1, self.width - fallback_width - 1)
                fallback_y = rnd.randint(1, self.height - fallback_height - 1)
                room = RoomRect(fallback_x, fallback_y, fallback_width, fallback_height)
                if not any(room.intersects(existing) for existing in self.rooms):
                    self.carve_room(room)
                    self.rooms.append(room)
                    placed = True
                    break

            if not placed:
                room = RoomRect(1, 1, fallback_width, fallback_height)
                self.carve_room(room)
                self.rooms.append(room)

        for index in range(1, len(self.rooms)):
            previous = self.rooms[index - 1].center
            current = self.rooms[index].center
            self.carve_corridor(previous, current, rnd)

        self.start = self.rooms[0].center
        self.exit = self.rooms[-1].center
        self.calculate_room_doors()
        self.populate_room_encounters(rnd)

    def carve_room(self, room: RoomRect) -> None:
        for y in range(room.top, room.bottom + 1):
            for x in range(room.left, room.right + 1):
                self.tiles[y][x] = Tile(x, y, (100, 100, 100), True)

    def carve_corridor(self, start: Tuple[int, int], end: Tuple[int, int], rnd: random.Random) -> None:
        x1, y1 = start
        x2, y2 = end
        if rnd.choice([True, False]):
            self.carve_horizontal_tunnel(x1, x2, y1)
            self.carve_vertical_tunnel(y1, y2, x2)
        else:
            self.carve_vertical_tunnel(y1, y2, x1)
            self.carve_horizontal_tunnel(x1, x2, y2)

    def carve_horizontal_tunnel(self, x1: int, x2: int, y: int) -> None:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.tiles[y][x] = Tile(x, y, (100, 100, 100), True)

    def carve_vertical_tunnel(self, y1: int, y2: int, x: int) -> None:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.tiles[y][x] = Tile(x, y, (100, 100, 100), True)

    def calculate_room_doors(self) -> None:
        for room in self.rooms:
            room.door_positions = []
            for x in range(room.left, room.right + 1):
                self._record_door_position(room, x, room.top)
                self._record_door_position(room, x, room.bottom)
            for y in range(room.top, room.bottom + 1):
                self._record_door_position(room, room.left, y)
                self._record_door_position(room, room.right, y)

    def _record_door_position(self, room: RoomRect, x: int, y: int) -> None:
        if not self.is_within_bounds(x, y):
            return
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.is_within_bounds(nx, ny) and not room.contains(nx, ny) and self.tiles[ny][nx].walkable:
                if (nx, ny) not in room.door_positions:
                    room.door_positions.append((nx, ny))

    def populate_room_encounters(self, rnd: random.Random) -> None:
        for index, room in enumerate(self.rooms):
            room.cleared = index == 0
            room.door_tile_snapshot = {}
            if room.cleared:
                room.encounter_positions = []
                continue
            positions = [
                (x, y)
                for x in range(room.left + 1, room.right)
                for y in range(room.top + 1, room.bottom)
                if self.tiles[y][x].walkable
            ]
            rnd.shuffle(positions)
            count = rnd.randint(1, min(3, max(1, len(positions))))
            room.encounter_positions = positions[:count]

    def lock_room(self, room: RoomRect) -> None:
        for x, y in room.door_positions:
            if (x, y) not in room.door_tile_snapshot:
                room.door_tile_snapshot[(x, y)] = self.tiles[y][x]
                self.tiles[y][x] = WallTile(x, y)

    def unlock_room(self, room: RoomRect) -> None:
        for (x, y), tile in list(room.door_tile_snapshot.items()):
            self.tiles[y][x] = tile
        room.door_tile_snapshot.clear()

    def is_within_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        return self.is_within_bounds(x, y) and self.tiles[y][x].walkable

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if self.is_within_bounds(x, y):
            return self.tiles[y][x]
        return None

    def get_floor_positions(self) -> list[Tuple[int, int]]:
        return [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if self.tiles[y][x].walkable
        ]

    def get_neighbor_positions(self, x: int, y: int) -> list[Tuple[int, int]]:
        candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        return [pos for pos in candidates if self.is_walkable(*pos)]

    def get_room_at(self, x: int, y: int) -> Optional[RoomRect]:
        return next((room for room in self.rooms if room.contains(x, y)), None)
