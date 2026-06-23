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
    def __init__(self, skills: str = 'test.json',
                 effects: str = 'test.json',
                 statuses: str = 'test.json'):
        self.skills = getcwd() + '\\' + skills
        self.effects = getcwd() + '\\' + effects
        self.statuses = getcwd() + '\\' + statuses

        self._data: Optional[dict] = None
        self._skill_cache: dict[str, Skill] = {}
        self._effect_cache: dict[str, Effect] = {}
        self._status_cache: dict[str, Status] = {}

    def _load_data(self) -> dict:
        if self._data is None:
            try:
                with open(self.skills, 'r', encoding='utf-8') as file:
                    self._data = json.load(file)
            except FileNotFoundError:
                raise FileNotFoundError(f"Data file not found: {self.skills}")
        return self._data

    def load_skill(self, id: str) -> Skill:
        if id in self._skill_cache:
            return self._skill_cache[id]

        data = self._load_data()
        info = next((obj for obj in data.get('skills', []) if obj['id'] == id), None)
        if info is None:
            raise ValueError(f"Skill '{id}' not found in {self.skills}")

        skill = Skill(
            name=info['name'],
            description=info.get('description', ''),
            cost=info.get('cost', 0),
            targeting_type=info.get('targeting_type', 'enemy'),
            dice=[Die(
                roll_range=die['range'],
                type=die['type'],
                effects=[Effect(
                    effect['trigger'],
                    effect['action'],
                    effect.get('condition'))
                    for effect in die.get('effects', [])]
            ) for die in info.get('dice', [])]
        )

        for effect_data in info.get('effects', []):
            skill.effects.append(Effect(
                effect_data['trigger'],
                effect_data['action'],
                effect_data.get('condition')
            ))

        self._skill_cache[id] = skill
        return skill

    def load_effect(self, id: str) -> Effect:
        if id in self._effect_cache:
            return self._effect_cache[id]

        data = self._load_data()
        info = next((obj for obj in data.get('effects', []) if obj['id'] == id), None)
        if info is None:
            raise ValueError(f"Effect '{id}' not found in {self.effects}")

        action = info.get('action')
        if action is None and info.get('actions'):
            action = info['actions'][0]

        effect = Effect(
            info['trigger'],
            action,
            info.get('condition')
        )

        self._effect_cache[id] = effect
        return effect

    def load_status(self, id: str) -> Status:
        if id in self._status_cache:
            return self._status_cache[id]

        data = self._load_data()
        info = next((obj for obj in data.get('statuses', []) if obj['id'] == id), None)
        if info is None:
            raise ValueError(f"Status '{id}' not found in {self.statuses}")

        status = Status(
            info['id'],
            info['name'],
            info.get('description', ''),
            decays=info.get('decays', True),
            effects=[self.load_effect(effect['id'])
                     for effect in info.get('effects', [])]
        )

        self._status_cache[id] = status
        return status

    def load_all_skills(self) -> dict[str, Skill]:
        if self._skill_cache:
            return dict(self._skill_cache)

        data = self._load_data()
        for info in data.get('skills', []):
            self.load_skill(info['id'])
        return dict(self._skill_cache)

    def load_all_effects(self) -> dict[str, Effect]:
        if self._effect_cache:
            return dict(self._effect_cache)

        data = self._load_data()
        for info in data.get('effects', []):
            self.load_effect(info['id'])
        return dict(self._effect_cache)

    def load_all_statuses(self) -> dict[str, Status]:
        results = {}
        data = self._load_data()
        for status_data in data.get('statuses', []):
            status = self.load_status(status_data['id'])
            results[status_data['id']] = status
            if status.name not in results:
                results[status.name] = status
        return results

    def load_enemy(self, id: str, pos: tuple[int, int] = (0, 0)) -> Creature:
        data = self._load_data()
        info = next((obj for obj in data.get('enemies', []) if obj['id'] == id), None)
        if info is None:
            raise ValueError(f"Enemy '{id}' not found in {self.skills}")

        deck = [self.load_skill(skill_id) for skill_id in info.get('deck', [])]
        random.shuffle(deck)
        enemy = Creature(
            name=info['name'],
            description=info.get('description', ''),
            HP=info.get('HP', 10),
            SR=info.get('SR', 10),
            resist=info.get('resist', {}),
            slots=[],
            deck=deck,
            max_points=info.get('max_points', -1),
            pos=pos
        )
        enemy.points = enemy.max_points if enemy.max_points > 0 else 0
        if enemy.deck:
            enemy.draw_skills(min(3, len(enemy.deck)))
        return enemy

    def create_random_enemy(self, pos: tuple[int, int] = (0, 0)) -> Creature:
        data = self._load_data()
        enemies = data.get('enemies', [])
        if not enemies:
            raise ValueError('No enemy definitions available')

        info = random.choice(enemies)
        return self.load_enemy(info['id'], pos)

    def get_random_skill_ids(self, count: int = 6) -> list[str]:
        data = self._load_data()
        ids = [obj['id'] for obj in data.get('skills', [])]
        if not ids:
            return []
        count = min(count, len(ids))
        return random.sample(ids, count)
