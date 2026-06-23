from interactible import Interactible
from skill import Skill
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from creature import Creature

class Skillslot(Interactible):
    def __init__(self, speed_range: tuple[int, int] = (0, 0)):
        self.assigned_skill: Skill = None
        self.target: 'Creature' = None  # Primary target creature for this slot
        self.target_positions: list[tuple[int, int]] = []  # Area target tiles for multi-target skills
        self.speed_range = speed_range
        self.speed = 0
        self.owner: 'Creature' = None
    
    def roll_speed(self) -> int:
        from random import randint
        self.speed = randint(self.speed_range[0], self.speed_range[1])
        return self.speed
    
    def get_speed(self) -> int:
        return self.speed
    
    def get_skill(self) -> Skill:
        return self.assigned_skill

    def set_target_creature(self, target: Optional['Creature']) -> None:
        self.target = target
        self.target_positions = []

    def get_target_creature(self) -> Optional['Creature']:
        return self.target

    def set_target_positions(self, positions: list[tuple[int, int]]) -> None:
        self.target_positions = list(positions)
        self.target = None

    def get_target_positions(self) -> list[tuple[int, int]]:
        return self.target_positions