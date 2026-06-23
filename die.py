from random import randint
from interactible import Interactible
from effect import Effect
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context import Context

class Die(Interactible):
    
    def __init__(self, roll_range: list[int],
                 type: str,
                 effects: list[Effect] = None):
        self.min_roll = roll_range[0]
        self.max_roll = roll_range[1]
        self.type = type
        self.effects = effects if effects is not None else []

    def roll(self, context: 'Context' = None) -> int:
        result = self.min_roll + randint(0, self.max_roll - self.min_roll)
        if context and result == self.max_roll:
            self.process_effects('on_die_max', context)
        return result
    
    def copy(self):
        return Die([self.min_roll, self.max_roll], self.type, list(self.effects))
    
    def process_effects(self, trigger: str, context: 'Context'):
        for effect in self.effects:
            if effect.trigger == trigger:
                effect.execute(context)
