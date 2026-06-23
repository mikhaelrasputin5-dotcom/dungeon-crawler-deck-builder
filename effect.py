from interactible import Interactible
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context import Context
    from creature import Creature

class Effect(Interactible):
    def __init__(self, trigger: str, action: dict, condition: dict = None):
        self.trigger = trigger
        self.action = action
        self.condition = condition
        
    def get_trigger(self):
        return self.trigger

    def get_action(self):
        return self.action
    
    def get_condition(self):
        return self.condition
    
    def _get_target_label(self) -> str:
        target = self.action.get('target')
        match target:
            case 'self':
                return 'self'
            case 'defender' | 'target':
                return 'target'
            case 'ally':
                return 'ally'
            case 'all_allies':
                return 'all allies'
            case 'enemy':
                return 'enemy'
            case 'all_enemies':
                return 'all enemies'
            case None:
                return 'target'
            case _:
                return str(target)

    def _resolve_targets(self, context: 'Context') -> list['Creature']:
        target = self.action.get('target')

        def alive(creature):
            return creature is not None and creature.is_alive()

        if target in (None, 'target', 'defender'):
            if context.targets:
                return [t for t in context.targets if alive(t)]
            if context.defender and alive(context.defender):
                return [context.defender]
            if context.target and alive(context.target):
                return [context.target]
            return []

        if target == 'self':
            return [context.attacker] if alive(context.attacker) else []

        if target in ('enemy', 'opponent'):
            if context.attacker and context.game:
                opponent = context.get_opponent(context.attacker)
                return [opponent] if alive(opponent) else []
            if context.defender and alive(context.defender):
                return [context.defender]
            return []

        if target in ('ally', 'all_allies'):
            if context.attacker and context.game:
                return [ally for ally in context.game.get_allies(context.attacker) if alive(ally)]
            return [context.attacker] if alive(context.attacker) else []

        if target == 'all_enemies':
            if context.attacker and context.game:
                if context.attacker == context.game.playerchar:
                    return [enemy for enemy in context.game.enemy_list if alive(enemy)]
                return [context.game.playerchar] if alive(context.game.playerchar) else []
            return []

        if target == 'all_targets':
            return [t for t in (context.targets or []) if alive(t)]

        return []

    def _describe_action(self) -> str:
        action_type = self.action.get('type')
        target_label = self._get_target_label()

        match action_type:
            case 'modify_max_roll':
                return f"Increase max roll by {self.action.get('value', 0)}"
            case 'modify_min_roll':
                return f"Increase min roll by {self.action.get('value', 0)}"
            case 'inflict_status':
                potency = self.action.get('potency', 0)
                status = self.action.get('status', 'status')
                count = self.action.get('count', 0)
                parts = []
                if potency:
                    parts.append(str(potency))
                parts.append(status.capitalize())
                desc = 'Inflict ' + ' '.join(parts)
                if count:
                    desc += f' ({count} stacks)'
                if target_label != 'target':
                    desc += f' on {target_label}'
                return desc
            case 'grant_next_turn_status':
                status = self.action.get('status', 'status')
                count = self.action.get('count', 0)
                potency = self.action.get('potency', 0)
                desc = f'Grant {status.capitalize()} next turn'
                if potency:
                    desc += f' ({potency})'
                if count:
                    desc += f' x{count}'
                if target_label != 'target':
                    desc += f' to {target_label}'
                return desc
            case 'double_damage':
                multiplier = self.action.get('multiplier', 2)
                return f'Double damage x{multiplier}'
            case 'heal':
                amount = self.action.get('amount', 0)
                return f'Heal {amount} to {target_label}'
            case 'damage_by_potency':
                status = self.action.get('status', 'status')
                multiplier = self.action.get('multiplier', 1)
                return f'Damage by {multiplier}x {status.capitalize()} potency to {target_label}'
            case 'restore_points':
                points = self.action.get('points', 1)
                return f'Restore {points} points to {target_label}'
            case 'restore_points_to_max':
                return f'Restore points to max for {target_label}'
            case 'draw_skills':
                count = self.action.get('count', 1)
                plural = 's' if count != 1 else ''
                return f'Draw {count} card{plural}'
            case 'draw_if_empty_hand':
                count = self.action.get('count', 1)
                return f'Draw {count} if hand empty'
            case 'refresh_if_deck_empty':
                return 'Refresh deck if empty'
            case 'refresh':
                return 'Refresh deck'
            case 'gain_shield':
                amount = self.action.get('amount', 0)
                return f'Gain {amount} shield'
            case _:
                return f'{action_type.replace('_', ' ').capitalize()}'

    def describe(self) -> str:
        trigger = self.trigger.replace('_', ' ').capitalize()
        action_desc = self._describe_action()
        return f'[{trigger}] {action_desc}'

    def check_condition(self, context: 'Context') -> bool:
        if not self.condition:
            return True
        
        match self.condition.get('type'):
        
            case 'status_count':
                target = context.defender if self.condition.get('subject') == 'target' else context.attacker
                status = self.condition['status']
                value = self.condition['value']
                return target.get_status_count(status) >= value

            case 'consecutive_wins':
                n = self.condition['count']
                history = context.clash_history
                if len(history) < n:
                    return False
                return all(my > their for my, their in history[-n:])

            case 'opponent_skill_type':
                if not hasattr(context, 'opponent_skill') or not context.opponent_skill:
                    return False
                return context.opponent_skill.targeting_type == self.condition.get('skill_type')
        
        return False

    def execute(self, context: 'Context') -> None:
        if not self.check_condition(context):
            return
        
        match self.action.get('type'):
        
            case 'modify_max_roll':
                if context.die:
                    context.die.max_roll += self.action.get('value', 1)

            case 'modify_min_roll':
                if context.die:
                    context.die.min_roll += self.action.get('value', 1)

            case 'inflict_status':
                potency = self.action.get('potency', 1)
                count = self.action.get('count', 1)
                status_name = self.action['status']
                status = None
                if hasattr(context, 'game') and context.game:
                    status = context.game.statuses.get(status_name)
                for target in self._resolve_targets(context):
                    target.add_status(status or status_name, potency, count)

            case 'grant_next_turn_status':
                potency = self.action.get('potency', 1)
                count = self.action.get('count', 1)
                for target in self._resolve_targets(context):
                    target.schedule_status(self.action['status'], potency, count, delay=1)

            case 'double_damage':
                context.damage *= self.action.get('multiplier', 2)

            case 'heal':
                amount = self.action.get('amount', 10)
                for target in self._resolve_targets(context):
                    target.HP = min(target.HP + amount, target.max_HP)
            
            case 'damage_by_potency':
                for target in self._resolve_targets(context):
                    status = target.get_status(self.action['status'])
                    if not status:
                        continue
                    damage = self.action.get('multiplier', 1) * status.potency
                    target.take_damage(damage, self.action.get('damage_type', 'true'), context)
                    if status.decay():
                        target.statuses.pop(self.action['status'], None)

            case 'restore_points':
                points = self.action.get('points', 1)
                for target in self._resolve_targets(context):
                    target.points = min(target.points + points, target.max_points)

            case 'restore_points_to_max':
                for target in self._resolve_targets(context):
                    target.points = target.max_points

            case 'draw_skills':
                count = self.action.get('count', 1)
                for target in self._resolve_targets(context):
                    target.draw_skills(count)

            case 'draw_if_empty_hand':
                count = self.action.get('count', 1)
                for target in self._resolve_targets(context):
                    if not target.hand:
                        target.draw_skills(count)

            case 'refresh_if_deck_empty':
                for target in self._resolve_targets(context):
                    if not target.deck and target.discarded:
                        target.refresh_deck()

            case 'refresh':
                for target in self._resolve_targets(context):
                    target.refresh_deck()

            case 'gain_shield':
                amount = self.action.get('amount', 0)
                for target in self._resolve_targets(context):
                    if hasattr(target, 'shield'):
                        target.shield += amount