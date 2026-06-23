import random
from typing import Optional, Tuple
from config import GW, GH
from tile import Tile, WallTile, CrumblingTile, HiddenTile, SlowTile

class RoomRect:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.enc_pos = []
        self.clr = False
        self.door_pos = []
        self.door_snap = {}

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.w - 1

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.h - 1

    @property
    def center(self):
        return (self.x + self.w // 2, self.y + self.h // 2)

    def intersects(self, o):
        return not (self.right < o.left - 1 or self.left > o.right + 1 or
                   self.bottom < o.top - 1 or self.top > o.bottom + 1)

    def contains(self, x, y):
        return self.left <= x <= self.right and self.top <= y <= self.bottom

class Floor:
    def __init__(self, w=GW, h=GH, seed=None):
        self.w = w
        self.h = h
        self.seed = seed if seed else random.randrange(2**31)
        self.rooms = []
        self.start = (1, 1)
        self.exit = (w - 2, h - 2)
        self.tiles = []
        self.gen()

    def gen(self):
        rnd = random.Random(self.seed)
        self.tiles = [[WallTile(x, y) for x in range(self.w)] for y in range(self.h)]
        self.rooms = []
        cnt = rnd.randint(3, 8)
        att = 0
        while len(self.rooms) < cnt and att < 60:
            rw = rnd.randint(5, min(10, self.w - 3))
            rh = rnd.randint(5, min(8, self.h - 3))
            max_x = max(1, self.w - rw - 2)
            max_y = max(1, self.h - rh - 2)
            rx = rnd.randint(1, max_x)
            ry = rnd.randint(1, max_y)
            room = RoomRect(rx, ry, rw, rh)
            if any(room.intersects(ex) for ex in self.rooms):
                att += 1
                continue
            self.carve_room(room)
            self.rooms.append(room)
            att += 1

        while len(self.rooms) < 3:
            fw = min(8, self.w - 2)
            fh = min(6, self.h - 2)
            pl = False
            for _ in range(10):
                fx = rnd.randint(1, self.w - fw - 1)
                fy = rnd.randint(1, self.h - fh - 1)
                room = RoomRect(fx, fy, fw, fh)
                if not any(room.intersects(ex) for ex in self.rooms):
                    self.carve_room(room)
                    self.rooms.append(room)
                    pl = True
                    break
            if not pl:
                room = RoomRect(1, 1, fw, fh)
                self.carve_room(room)
                self.rooms.append(room)

        for i in range(1, len(self.rooms)):
            prev = self.rooms[i - 1].center
            cur = self.rooms[i].center
            self.carve_corr(prev, cur, rnd)

        self.start = self.rooms[0].center
        self.exit = self.rooms[-1].center
        self.calc_doors()
        self.pop_enc(rnd)

    def carve_room(self, room):
        for y in range(room.top, room.bottom + 1):
            for x in range(room.left, room.right + 1):
                self.tiles[y][x] = Tile(x, y, (100, 100, 100), True)

    def carve_corr(self, s, e, rnd):
        x1, y1 = s
        x2, y2 = e
        if rnd.choice([True, False]):
            self.carve_h_tun(x1, x2, y1)
            self.carve_v_tun(y1, y2, x2)
        else:
            self.carve_v_tun(y1, y2, x1)
            self.carve_h_tun(x1, x2, y2)

    def carve_h_tun(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.tiles[y][x] = Tile(x, y, (100, 100, 100), True)

    def carve_v_tun(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.tiles[y][x] = Tile(x, y, (100, 100, 100), True)

    def calc_doors(self):
        for room in self.rooms:
            room.door_pos = []
            for x in range(room.left, room.right + 1):
                self.rec_door(room, x, room.top)
                self.rec_door(room, x, room.bottom)
            for y in range(room.top, room.bottom + 1):
                self.rec_door(room, room.left, y)
                self.rec_door(room, room.right, y)

    def rec_door(self, room, x, y):
        if not self.in_bounds(x, y):
            return
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny) and not room.contains(nx, ny) and self.tiles[ny][nx].walkable:
                if (nx, ny) not in room.door_pos:
                    room.door_pos.append((nx, ny))

    def pop_enc(self, rnd):
        for i, room in enumerate(self.rooms):
            room.clr = i == 0
            room.door_snap = {}
            if room.clr:
                room.enc_pos = []
                continue
            pos = [(x, y) for x in range(room.left + 1, room.right)
                   for y in range(room.top + 1, room.bottom)
                   if self.tiles[y][x].walkable]
            rnd.shuffle(pos)
            cnt = rnd.randint(1, min(3, max(1, len(pos))))
            room.enc_pos = pos[:cnt]

    def lock_room(self, room):
        for x, y in room.door_pos:
            if (x, y) not in room.door_snap:
                room.door_snap[(x, y)] = self.tiles[y][x]
                self.tiles[y][x] = WallTile(x, y)

    def unlock_room(self, room):
        for (x, y), tile in list(room.door_snap.items()):
            self.tiles[y][x] = tile
        room.door_snap.clear()

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def is_walk(self, x, y):
        return self.in_bounds(x, y) and self.tiles[y][x].walkable

    def get_tile(self, x, y):
        if self.in_bounds(x, y):
            return self.tiles[y][x]
        return None

    def get_floor_pos(self):
        return [(x, y) for y in range(self.h)
                for x in range(self.w) if self.tiles[y][x].walkable]

    def get_neigh(self, x, y):
        cand = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        return [pos for pos in cand if self.is_walk(*pos)]

    def get_room_at(self, x, y):
        return next((room for room in self.rooms if room.contains(x, y)), None)
