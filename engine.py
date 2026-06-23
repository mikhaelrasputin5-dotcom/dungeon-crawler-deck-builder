import json
import random
from os import getcwd
from typing import Optional
from creature import Creature
from die import Die
from effect import Effect
from skill import Skill
from status import Status

class Engine:
    def __init__(self, sk_f='test.json', fx_f='test.json', st_f='test.json'):
        self.sk_f = getcwd() + '\\' + sk_f
        self.fx_f = getcwd() + '\\' + fx_f
        self.st_f = getcwd() + '\\' + st_f
        self._d = None
        self._sk_c = {}
        self._fx_c = {}
        self._st_c = {}

    def _load(self):
        if self._d is None:
            try:
                with open(self.sk_f, 'r', encoding='utf-8') as f:
                    self._d = json.load(f)
            except FileNotFoundError:
                raise FileNotFoundError(f"Data file not found: {self.sk_f}")
        return self._d

    def load_sk(self, id):
        if id in self._sk_c:
            return self._sk_c[id]
        d = self._load()
        inf = next((obj for obj in d.get('skills', []) if obj['id'] == id), None)
        if inf is None:
            raise ValueError(f"Skill '{id}' not found in {self.sk_f}")
        sk = Skill(
            inf['name'], inf.get('description', ''), inf.get('cost', 0),
            inf.get('targeting_type', 'enemy'),
            [Die(die['range'], die['type'],
                 [Effect(e['trigger'], e['action'], e.get('condition'))
                  for e in die.get('effects', [])])
             for die in inf.get('dice', [])]
        )
        for ed in inf.get('effects', []):
            sk.effects.append(Effect(ed['trigger'], ed['action'], ed.get('condition')))
        self._sk_c[id] = sk
        return sk

    def load_fx(self, id):
        if id in self._fx_c:
            return self._fx_c[id]
        d = self._load()
        inf = next((obj for obj in d.get('effects', []) if obj['id'] == id), None)
        if inf is None:
            raise ValueError(f"Effect '{id}' not found in {self.fx_f}")
        act = inf.get('action')
        if act is None and inf.get('actions'):
            act = inf['actions'][0]
        fx = Effect(inf['trigger'], act, inf.get('condition'))
        self._fx_c[id] = fx
        return fx

    def load_st(self, id):
        if id in self._st_c:
            return self._st_c[id]
        d = self._load()
        inf = next((obj for obj in d.get('statuses', []) if obj['id'] == id), None)
        if inf is None:
            raise ValueError(f"Status '{id}' not found in {self.st_f}")
        st = Status(
            inf['id'], inf['name'], inf.get('description', ''),
            decays=inf.get('decays', True),
            effects=[self.load_fx(e['id']) for e in inf.get('effects', [])]
        )
        self._st_c[id] = st
        return st

    def load_all_sk(self):
        if self._sk_c:
            return dict(self._sk_c)
        d = self._load()
        for inf in d.get('skills', []):
            self.load_sk(inf['id'])
        return dict(self._sk_c)

    def load_all_fx(self):
        if self._fx_c:
            return dict(self._fx_c)
        d = self._load()
        for inf in d.get('effects', []):
            self.load_fx(inf['id'])
        return dict(self._fx_c)

    def load_all_st(self):
        res = {}
        d = self._load()
        for sd in d.get('statuses', []):
            st = self.load_st(sd['id'])
            res[sd['id']] = st
            if st.name not in res:
                res[st.name] = st
        return res

    def load_enemy(self, id, pos=(0, 0)):
        d = self._load()
        inf = next((obj for obj in d.get('enemies', []) if obj['id'] == id), None)
        if inf is None:
            raise ValueError(f"Enemy '{id}' not found in {self.sk_f}")
        deck = [self.load_sk(sid) for sid in inf.get('deck', [])]
        random.shuffle(deck)
        enem = Creature(
            inf['name'], inf.get('description', ''), inf.get('HP', 10),
            inf.get('SR', 10), inf.get('resist', {}), [], deck,
            max_pts=inf.get('max_points', -1), pos=pos
        )
        enem.pts = enem.max_pts if enem.max_pts > 0 else 0
        if enem.deck:
            enem.draw_sk(min(3, len(enem.deck)))
        return enem

    def create_rand_enemy(self, pos=(0, 0)):
        d = self._load()
        enemies = d.get('enemies', [])
        if not enemies:
            raise ValueError('No enemy definitions available')
        inf = random.choice(enemies)
        return self.load_enemy(inf['id'], pos)

    def get_rand_sk_ids(self, cnt=6):
        d = self._load()
        ids = [obj['id'] for obj in d.get('skills', [])]
        if not ids:
            return []
        cnt = min(cnt, len(ids))
        return random.sample(ids, cnt)
