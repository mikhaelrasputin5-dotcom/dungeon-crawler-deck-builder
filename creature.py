import random
from typing import TYPE_CHECKING
from interactible import Interactible
from skill import Skill
from skillslot import Skillslot
from effect import Effect
from status import Status

if TYPE_CHECKING:
    from game import Game
    from context import Context

class Creature(Interactible):
    
    def __init__(self,
                 name: str, description: str,
                 HP: int, SR: int, resist: dict[str, int],
                 slots: list[Skillslot],
                 deck: list[Skill],
                 max_points: int = -1,
                 pos: tuple[int, int] = (0, 0)):
        self.name = name
        self.description = description
        self.HP = HP
        self.max_HP = HP
        self.SR = SR  # Stagger resistance
        self.max_SR = SR
        self.resist = resist

        self.slots = slots
        self.deck = deck
        self.hand: list[Skill] = []
        self.discarded: list[Skill] = []
        self.points = 0
        self.max_points = max_points
        self.staggered_turns = 0

        self.pos = pos

        self.effects: list[Effect] = []
        self.statuses: dict[str, Status] = {}
        self.pending_statuses: list[dict] = []
        self.shield = 0

        self.layout: 'Game' = None  # Assigned by Game.add_enemy()

    def apply(self, status: Status, potency: int = 0, count: int = 0) -> None:
        key = getattr(status, 'id', status.name)
        if key not in self.statuses:
            self.statuses[key] = status.copy()
            self.statuses[key].potency = potency or status.potency
            self.statuses[key].count = count or status.count
        else:
            self.statuses[key].potency += potency
            self.statuses[key].count += count
    
    def add_status(self, status: Status | str, potency: int = 0, count: int = 0) -> None:
        if isinstance(status, str):
            if self.layout and status in self.layout.statuses:
                status = self.layout.statuses[status]
            else:
                status = Status(status, status, '')
        self.apply(status, potency, count)
        if self.layout:
            label = f'+{status.name}'
            if count:
                label += f' x{count}'
            self.layout.add_status_number(self, label)
    
    def get_status(self, name: str) -> Status | None:
        status = self.statuses.get(name)
        if status:
            return status
        for status in self.statuses.values():
            if status.name == name:
                return status
        return None
    
    def get_status_count(self, name: str) -> int:
        status = self.get_status(name)
        return status.count if status else 0
    
    def schedule_status(self, status: Status | str, potency: int = 0, count: int = 0, delay: int = 1) -> None:
        if isinstance(status, Status):
            status = status.id
        self.pending_statuses.append({'status': status, 'potency': potency, 'count': count, 'delay': delay})
    
    def apply_pending_statuses(self) -> None:
        remaining = []
        for pending in self.pending_statuses:
            pending['delay'] -= 1
            if pending['delay'] <= 0:
                status = pending['status']
                if isinstance(status, str) and self.layout:
                    status = self.layout.statuses.get(status)
                if isinstance(status, str):
                    status = Status(status, status, '')
                self.add_status(status, pending['potency'], pending['count'])
            else:
                remaining.append(pending)
        self.pending_statuses = remaining

    def decay_status(self) -> None:
        for name in self.statuses.copy():
            if self.statuses[name].decay():
                self.statuses.pop(name)

    def take_damage(self, damage: int, dtype: str, context: 'Context' = None):
        prev_HP = int(self.HP)
        adjusted_damage = int(damage * (1 - self.resist.get(dtype + '_HP', 0)))

        if self.shield > 0 and adjusted_damage > 0:
            blocked = min(self.shield, adjusted_damage)
            self.shield -= blocked
            adjusted_damage -= blocked
            if adjusted_damage <= 0:
                if context:
                    context.damage = 0
                    context.hp_lost = 0
                    context.hp_percent_lost = 0
                return

        self.HP -= adjusted_damage

        if adjusted_damage > 0 and self.layout:
            self.layout.add_damage_number(self, adjusted_damage)
            self.layout.add_attack_animation(self, dtype)

        if context:
            context.damage = adjusted_damage
            context.hp_lost = prev_HP - self.HP
            context.hp_percent_lost = (prev_HP - self.HP) * 100 / prev_HP if prev_HP > 0 else 0
            self.process_effects('on_hit', context)
        
        if self.SR > 0:
            sr_damage = int(adjusted_damage * (1 - self.resist.get(dtype + '_SR', 0)))
            self.SR = max(0, self.SR - sr_damage)
            
            if self.is_staggered() and context:
                self.process_effects('on_stagger', context)
                if self.layout:
                    self.layout.handle_stagger(self, context)

        if self.HP <= 0 and self.layout and context:
            self.layout.handle_death(self, context)

    def heal(self, amount: int) -> None:
        if self.HP > 0:
            self.HP = min(self.max_HP, self.HP + amount)

    def is_alive(self) -> bool:
        return self.HP > 0

    def is_staggered(self) -> bool:
        return self.SR <= 0

    def take_manual_turn(self) -> None:
        self.autopilot()
    
    def autopilot(self) -> None:
        if not self.hand:
            return

        affordable = [s for s in self.hand if self.points >= s.cost] if self.max_points > 0 else list(self.hand)
        if not affordable:
            return

        skill = random.choice(affordable)
        if self.max_points > 0:
            self.points -= skill.cost
        
        if self.layout:
            target = None
            if self == self.layout.playerchar:
                target = next((e for e in self.layout.enemy_list if e.is_alive()), None)
            else:
                target = self.layout.playerchar if self.layout.playerchar.is_alive() else None
            
            slot = Skillslot(speed_range=(0, 0))
            slot.owner = self
            slot.set_target_creature(target)
            slot.assigned_skill = skill
            slot.roll_speed()
            self.layout.add_slot(slot)

    def assignSlot(self, slot: Skillslot) -> bool:
        if slot in self.slots:
            return False
        self.slots.append(slot)
        return True
    
    def draw_skills(self, n: int = 1) -> None:
        if not self.deck and self.discarded:
            self.refresh_deck()
        for _ in range(n):
            if self.deck:
                self.hand.append(self.deck.pop(0))

    def discard(self, skill: Skill, context: 'Context') -> None:
        if skill in self.hand:
            self.hand.remove(skill)
            self.discarded.append(skill)
            self.process_effects('on_discard', context)
    
    def refresh_deck(self) -> None:
        if self.discarded:
            self.deck.extend(self.discarded)
            self.discarded.clear()
            random.shuffle(self.deck)

    def get_effect_list(self):
        return self.effects.copy()
    
    def process_effects(self, trigger: str, context: 'Context') -> None:
        for effect in self.effects:
            if effect.trigger == trigger:
                effect.execute(context)
        self.process_status_effects(trigger, context)
    
    def process_status_effects(self, trigger: str, context: 'Context') -> None:
        for status in list(self.statuses.values()):
            for effect in status.effects:
                if effect.trigger == trigger:
                    effect.execute(context)