from random import randint
from typing import TYPE_CHECKING
from die import Die
from effect import Effect

if TYPE_CHECKING:
    from creature import Creature
    from context import Context

class Skill:
    def __init__(self, name: str, description: str,
                 cost: int,
                 targeting_type: str,
                 dice: list[Die]):
        self.name = name
        self.description = description
        self.cost = cost
        self.targeting_type = targeting_type  # 'self', 'enemy', 'cone', etc.
        self.dice = dice
        self.effects: list[Effect] = []

    def clash(self, other_skill: 'Skill', context: 'Context') -> int:
        self.process_effects('on_play', context)
        self.process_effects('on_clash_start', context)
        my_dice = [d.copy() for d in self.dice]
        their_dice = [d.copy() for d in other_skill.dice]

        fin = 0
        
        original_attacker = context.attacker
        original_defender = context.defender

        for index in range(min(len(my_dice), len(their_dice))):
            self.process_effects('on_clash', context)
            
            my_die = my_dice[index]
            their_die = their_dice[index]
            
            context.die = my_die
            context.index = index
            context.attacker = original_attacker
            context.defender = original_defender
            context.attacker.process_effects('on_die_roll', context)
            my_die.process_effects('on_die_roll', context)
            
            context.die = their_die
            context.attacker = original_defender
            context.defender = original_attacker
            context.attacker.process_effects('on_die_roll', context)
            their_die.process_effects('on_die_roll', context)
            
            context.attacker = original_attacker
            context.defender = original_defender
            my_roll = my_die.roll(context)
            their_roll = their_die.roll(context)
            
            context.clash_history.append((my_roll, their_roll))
            
            if my_roll > their_roll:
                context.damage = my_roll - their_roll
                context.die = my_die
                my_die.process_effects('on_win', context)
                if my_die.type == 'evade':
                    my_die.process_effects('on_evade_success', context)
                    context.damage = 0

                context.die = their_die
                their_die.process_effects('on_lose', context)
                if their_die.type == 'evade':
                    their_die.process_effects('on_evade_fail', context)

                target = context.get_opponent(context.attacker)
                target.take_damage(context.damage, my_die.type, context)
            elif their_roll > my_roll:
                context.damage = their_roll - my_roll
                context.die = their_die
                their_die.process_effects('on_win', context)
                if their_die.type == 'evade':
                    their_die.process_effects('on_evade_success', context)
                    context.damage = 0

                context.die = my_die
                my_die.process_effects('on_lose', context)
                if my_die.type == 'evade':
                    my_die.process_effects('on_evade_fail', context)

                target = context.get_opponent(context.defender)
                target.take_damage(context.damage, their_die.type, context)
            context.damage = 0
            fin += 1
        return fin
        
    def attack(self, context: 'Context', begin: int = 0):
        self.process_effects('on_play', context)
        self.process_effects('on_unopposed_attack', context)

        for index, die in enumerate(self.dice):
            if index < begin or die.type == 'evade':
                continue

            context.die = die
            context.index = index
            context.attacker.process_effects('on_die_roll', context)
            die.process_effects('on_die_roll', context)
            context.damage = die.roll(context)

            targets = context.targets
            if not targets:
                primary_target = context.defender or context.get_opponent(context.attacker)
                targets = [primary_target] if primary_target else []

            for target in targets:
                if target is None or not target.is_alive():
                    continue
                target_context = context.with_target(target)
                die.process_effects('on_unopposed_hit', target_context)
                target.take_damage(context.damage, die.type, target_context)

            context.damage = 0
    
    def process_effects(self, trigger: str, context: 'Context') -> None:
        for effect in self.effects:
            if effect.trigger == trigger:
                effect.execute(context)