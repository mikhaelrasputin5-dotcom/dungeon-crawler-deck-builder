from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from creature import Creature
    from skill import Skill
    from skillslot import Skillslot
    from die import Die

class Context:
    
    def __init__(self, **kwargs):
        self.phase: str = kwargs.get('phase')
        self.game = kwargs.get('game')
        self.source = kwargs.get('source')
        self.event_data = kwargs.get('event_data', {})
        
        self.actor: Creature = kwargs.get('actor')
        self.target: Creature = kwargs.get('target')

        self.attacker: Creature = kwargs.get('attacker')
        self.defender: Creature = kwargs.get('defender')
        self.skill: Skill = kwargs.get('skill')
        self.opponent_skill: Skill = kwargs.get('opponent_skill')
        self.slot: Skillslot = kwargs.get('slot')
        self.opponent_slot: Skillslot = kwargs.get('opponent_slot')
        self.die: Die = kwargs.get('die')
        self.index: int = kwargs.get('index')
        self.clash_history = kwargs.get('clash_history', [])
        self.damage: int = kwargs.get('damage', 0)
        self.targets: Optional[list[Creature]] = kwargs.get('targets')
        self.target_positions: list[tuple[int, int]] = kwargs.get('target_positions', [])
        self.hp_lost: int = kwargs.get('hp_lost', 0)
        self.hp_percent_lost: float = kwargs.get('hp_percent_lost', 0)

    def with_die(self, die, index):
        new_context = Context(
            phase=self.phase,
            game=self.game,
            source=self.source,
            event_data=self.event_data.copy() if isinstance(self.event_data, dict) else self.event_data,

            actor=self.actor,
            target=self.target,

            attacker=self.attacker,
            defender=self.defender,
            skill=self.skill,
            opponent_skill=self.opponent_skill,
            slot=self.slot,
            opponent_slot=self.opponent_slot,
            die=die,
            index=index,
            clash_history=list(self.clash_history),
            damage=self.damage,
            hp_lost=self.hp_lost,
            hp_percent_lost=self.hp_percent_lost,
            targets=list(self.targets) if self.targets is not None else None,
            target_positions=list(self.target_positions)
        )
        return new_context

    def with_target(self, target: 'Creature') -> 'Context':
        new_context = Context(
            phase=self.phase,
            game=self.game,
            source=self.source,
            event_data=self.event_data.copy() if isinstance(self.event_data, dict) else self.event_data,

            actor=self.actor,
            target=target,

            attacker=self.attacker,
            defender=target,
            skill=self.skill,
            opponent_skill=self.opponent_skill,
            slot=self.slot,
            opponent_slot=self.opponent_slot,
            die=self.die,
            index=self.index,
            clash_history=list(self.clash_history),
            damage=self.damage,
            targets=list(self.targets) if self.targets is not None else None,
            target_positions=list(self.target_positions),
            hp_lost=self.hp_lost,
            hp_percent_lost=self.hp_percent_lost
        )
        return new_context

    def restore_die(self, die, index):
        self.die = die
        self.index = index
    
    def get_opponent(self, creature) -> 'Creature':
        if creature == self.attacker:
            return self.defender
        return self.attacker
    
    def get_allies(self, creature) -> list['Creature']:
        if creature in self.game.enemy_list:
            return self.game.enemy_list
        return [self.game.playerchar]