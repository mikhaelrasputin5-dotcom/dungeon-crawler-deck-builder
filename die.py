from random import randint
from interactible import Interactible
from effect import Effect
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context import Context

class Die(Interactible):
    def __init__(self, rng, t, fx=None):
        self.min_roll = rng[0]
        self.max_roll = rng[1]
        self.type = t
        self.effects = fx if fx else []

    def roll(self, ctx=None):
        r = self.min_roll + randint(0, self.max_roll - self.min_roll)
        if ctx and r == self.max_roll:
            self.fx_proc('on_die_max', ctx)
        return r

    def copy(self):
        return Die([self.min_roll, self.max_roll], self.type, list(self.effects))

    def fx_proc(self, t, ctx):
        for e in self.effects:
            if e.trigger == t:
                e.execute(ctx)
    
    def process_effects(self, t, ctx):
        self.fx_proc(t, ctx)
