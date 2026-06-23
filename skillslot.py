from interactible import Interactible
from skill import Skill
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from creature import Creature

class Skillslot(Interactible):
    def __init__(self, speed_range=(0, 0)):
        self.sk = None
        self.tgt = None
        self.tgt_pos = []
        self.spd_rng = speed_range
        self.spd = 0
        self.owner = None
    
    def roll_spd(self):
        from random import randint
        self.spd = randint(self.spd_rng[0], self.spd_rng[1])
        return self.spd
    
    def get_speed(self):
        return self.spd
    
    def get_skill(self):
        return self.sk
    
    def assigned_skill(self):
        return self.sk
    
    @property
    def assigned_skill(self):
        return self.sk
    
    @assigned_skill.setter
    def assigned_skill(self, val):
        self.sk = val
    
    @property
    def target(self):
        return self.tgt
    
    @target.setter
    def target(self, val):
        self.tgt = val

    def set_target_creature(self, t):
        self.tgt = t
        self.tgt_pos = []

    def get_target_creature(self):
        return self.tgt

    def set_target_positions(self, pos):
        self.tgt_pos = list(pos)
        self.tgt = None

    def get_target_positions(self):
        return self.tgt_pos
