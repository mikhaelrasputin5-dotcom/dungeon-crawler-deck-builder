from enum import Enum, auto
import random
from pathlib import Path
from typing import Optional

import pygame
from pygame import Vector2

from creature import Creature
from skillslot import Skillslot
from context import Context
from engine import Engine
from floor import Floor, RoomRect
from tile import HiddenTile
from config import GRID_WIDTH, GRID_HEIGHT, TILE_SIZE, COLOR_BG

class GameState(Enum):
    INIT = auto()
    EXPLORING = auto()
    COMBAT = auto()
    LOOT = auto()
    GAME_OVER = auto()

class Game:
    def __init__(self, playerchar: Creature, width: int = GRID_WIDTH, height: int = GRID_HEIGHT, seed: int | None = None, engine: Engine | None = None):
        self.playerchar = playerchar
        self.enemy_list = []
        self.res_order: list[Skillslot] = []
        self.engine = engine if engine is not None else Engine()
        self.state = GameState.INIT
        self.seed = seed if seed is not None else random.randrange(2**31)
        self.floor = Floor(width, height, seed=self.seed)
        self.current_floor = 1
        self.playerchar.pos = self.floor.start
        self.playerchar.layout = self
        self.playerchar.points = self.playerchar.max_points if self.playerchar.max_points > 0 else 0
        self.player_room: RoomRect | None = self.floor.get_room_at(*self.playerchar.pos)
        self.combat_room: RoomRect | None = None
        self.statuses = self.engine.load_all_statuses()
        self.resolution_queue: list[dict] = []
        self.current_resolution_event: dict | None = None
        self.resolution_active = False
        self.damage_numbers: list[dict] = []
        self.status_numbers: list[dict] = []
        self.attack_animations: list[dict] = []
        self.attack_animation_frames: dict[str, list[pygame.Surface]] = {}
        self._load_attack_animation_frames()

        try:
            self.playerchar.effects.append(self.engine.load_effect('restore_points'))
        except ValueError:
            pass

        self.apply_default_turn_end_effects(self.playerchar)
        self.set_state(GameState.EXPLORING)

    def add_damage_number(self, creature: Creature, amount: int) -> None:
        if amount <= 0:
            return
        extra = self._popup_stack_offset(creature)
        x = creature.pos[0] * TILE_SIZE + TILE_SIZE // 2 + extra[0]
        y = creature.pos[1] * TILE_SIZE + extra[1]
        self.damage_numbers.append({
            'target': creature,
            'text': f'-{amount}',
            'x': x,
            'y': y,
            'vy': -40,
            'age': 0,
            'duration': 900,
            'color': (255, 80, 80),
        })

    def add_status_number(self, creature: Creature, text: str) -> None:
        if not text:
            return
        extra = self._popup_stack_offset(creature)
        x = creature.pos[0] * TILE_SIZE + TILE_SIZE // 2 + extra[0]
        y = creature.pos[1] * TILE_SIZE + extra[1]
        self.status_numbers.append({
            'target': creature,
            'text': text,
            'x': x,
            'y': y,
            'vy': -40,
            'age': 0,
            'duration': 900,
            'color': (100, 220, 220),
        })

    def _popup_stack_offset(self, creature: Creature) -> tuple[int, int]:
        existing = [n for n in self.damage_numbers + self.status_numbers if n['target'] == creature]
        offset_index = len(existing)
        x_offset = (offset_index % 2) * 12 - 6
        y_offset = offset_index * 16
        return (x_offset, y_offset)

    def _load_attack_animation_frames(self) -> None:
        animation_dir = Path(__file__).resolve().parent / 'animations'
        self.attack_animation_frames = {}

        for kind in ('blunt', 'slash', 'pierce'):
            path = animation_dir / f'basic_{kind}.png'
            try:
                sheet = pygame.image.load(str(path))
            except pygame.error:
                continue

            frame_height = sheet.get_height()
            if frame_height <= 0:
                continue

            frame_count = max(1, sheet.get_width() // frame_height)
            frame_width = sheet.get_width() // frame_count
            frames = [
                sheet.subsurface(pygame.Rect(i * frame_width, 0, frame_width, frame_height)).copy()
                for i in range(frame_count)
            ]
            self.attack_animation_frames[kind] = frames

    def add_attack_animation(self, creature: Creature, damage_type: str) -> None:
        key = 'slash'
        lowered = damage_type.lower()
        if 'blunt' in lowered:
            key = 'blunt'
        elif 'slash' in lowered:
            key = 'slash'
        elif 'pierce' in lowered:
            key = 'pierce'

        frames = self.attack_animation_frames.get(key)
        if not frames:
            self._load_attack_animation_frames()
            frames = self.attack_animation_frames.get(key)

        if not frames:
            return

        self.attack_animations.append({
            'target': creature,
            'frames': frames,
            'age': 0,
            'duration': 220,
            'offset': (0, -6),
        })

    def update_damage_numbers(self, dt: int) -> None:
        if not self.damage_numbers and not self.status_numbers:
            return

        remaining_damage = []
        for number in self.damage_numbers:
            number['age'] += dt
            number['y'] += number['vy'] * (dt / 1000.0)
            if number['age'] < number['duration']:
                remaining_damage.append(number)
        self.damage_numbers = remaining_damage

        remaining_status = []
        for number in self.status_numbers:
            number['age'] += dt
            number['y'] += number['vy'] * (dt / 1000.0)
            if number['age'] < number['duration']:
                remaining_status.append(number)
        self.status_numbers = remaining_status

    def update_attack_animations(self, dt: int) -> None:
        if not self.attack_animations:
            return

        remaining = []
        for animation in self.attack_animations:
            animation['age'] += dt
            if animation['age'] < animation['duration']:
                remaining.append(animation)
        self.attack_animations = remaining

    def draw_attack_animations(self, surface, offset: tuple[int, int] = (0, 0)) -> None:
        for animation in self.attack_animations:
            progress = min(1.0, animation['age'] / animation['duration'])
            index = min(len(animation['frames']) - 1, int(progress * len(animation['frames'])))
            frame = animation['frames'][index]
            x = animation['target'].pos[0] * TILE_SIZE + TILE_SIZE // 2 + offset[0] + animation['offset'][0]
            y = animation['target'].pos[1] * TILE_SIZE + TILE_SIZE // 2 + offset[1] + animation['offset'][1]
            rect = frame.get_rect(center=(x, y))
            surface.blit(frame, rect)

    def set_state(self, new_state: GameState) -> None:
        self.state = new_state

    def apply_default_turn_end_effects(self, creature: Creature) -> None:
        for effect_id in ['refresh_if_deck_empty', 'draw_if_empty_hand']:
            try:
                creature.effects.append(self.engine.load_effect(effect_id))
            except ValueError:
                pass

    def create_floor(self, seed: int | None = None, screen=None) -> None:
        self.seed = seed if seed is not None else random.randrange(2**31)
        self.floor = Floor(self.floor.width, self.floor.height, seed=self.seed)
        self.playerchar.pos = self.floor.start
        self.player_room = self.floor.get_room_at(*self.playerchar.pos)
        if screen is not None:
            self._render_floor_in_pygame(screen)

    def advance_floor(self, screen=None) -> None:
        self.current_floor += 1
        self.create_floor(screen=screen)
        self.set_state(GameState.EXPLORING)

    def _render_floor_in_pygame(self, surface) -> None:
        pygame.event.pump()
        surface.fill(COLOR_BG)
        self.draw_floor(surface)
        pygame.display.flip()

    def draw_floor(self, surface, offset: tuple[int, int] = (0, 0)) -> None:
        player_pixel = Vector2(
            self.playerchar.pos[0] * TILE_SIZE + TILE_SIZE / 2 + offset[0],
            self.playerchar.pos[1] * TILE_SIZE + TILE_SIZE / 2 + offset[1]
        )

        for row in self.floor.tiles:
            for tile in row:
                if isinstance(tile, HiddenTile):
                    tile.draw(surface, player_pixel, offset)
                else:
                    tile.draw(surface, offset)

        pygame.draw.circle(surface, (255, 50, 50), player_pixel, TILE_SIZE // 3)

        if self.floor.start is not None:
            start_pixel = Vector2(
                self.floor.start[0] * TILE_SIZE + TILE_SIZE / 2 + offset[0],
                self.floor.start[1] * TILE_SIZE + TILE_SIZE / 2 + offset[1]
            )
            pygame.draw.circle(surface, (50, 255, 50), start_pixel, TILE_SIZE // 4)

        if self.floor.exit is not None:
            pygame.draw.rect(
                surface,
                (255, 255, 50),
                pygame.Rect(
                    self.floor.exit[0] * TILE_SIZE + offset[0],
                    self.floor.exit[1] * TILE_SIZE + offset[1],
                    TILE_SIZE,
                    TILE_SIZE,
                ),
                2,
            )

    def can_walk(self, x: int, y: int) -> bool:
        return self.floor.is_walkable(x, y)

    def move_player(self, dx: int, dy: int) -> bool:
        if self.state != GameState.EXPLORING:
            return False

        x, y = self.playerchar.pos
        target_x, target_y = x + dx, y + dy
        if not self.can_walk(target_x, target_y):
            return False

        self.playerchar.pos = (target_x, target_y)
        tile = self.floor.get_tile(target_x, target_y)
        if tile is not None:
            tile.on_enter(self, self.playerchar)

        new_room = self.floor.get_room_at(target_x, target_y)
        previous_room = self.player_room
        if new_room is not previous_room:
            self.player_room = new_room
            enemies = self.encounter_found(new_room)
            if enemies:
                self.enter_combat(enemies, new_room)
                return True

        if self.state == GameState.EXPLORING and (target_x, target_y) == self.floor.exit:
            self.advance_floor()

        return True

    def update(self, action: dict | None = None) -> bool:
        if self.state != GameState.EXPLORING or action is None:
            return False

        match action.get('type'):
            case 'move' if isinstance(action.get('direction'), tuple):
                dx, dy = action['direction']
                return self.move_player(dx, dy)
            case _:
                return False

    def enter_combat(self, enemies: list[Creature], room: RoomRect | None = None) -> None:
        self.enemy_list = enemies
        self.res_order.clear()
        self.combat_room = room
        if room is not None:
            self.floor.lock_room(room)
        self.set_state(GameState.COMBAT)
        self.begin_turn()

    def begin_turn(self) -> None:
        self.res_order.clear()
        self.playerchar.apply_pending_statuses()
        for enemy in self.enemy_list:
            if enemy.is_alive():
                enemy.apply_pending_statuses()

        mass_context = Context(game=self, target=None, slot=None, damage=0)
        self.mass_broadcast('turn_start', 'turn_start', mass_context)
        self.autopilot_enemies()
        if self.playerchar.is_staggered() and any(slot.owner != self.playerchar for slot in self.res_order):
            self.execute_turn()

    def autopilot_enemies(self) -> None:
        for enemy in self.enemy_list:
            if enemy.is_alive() and not enemy.is_staggered():
                enemy.autopilot()

    def execute_turn(self) -> None:
        mass_context = Context(game=self, target=None, slot=None, damage=0)
        self.mass_broadcast('resolve_start', 'resolve_start', mass_context)
        self.start_resolution()

    def start_resolution(self) -> None:
        self.resolution_queue = []
        self.current_resolution_event = None
        self.resolution_active = False
        self._build_resolution_queue()
        if self.resolution_queue:
            self.resolution_active = True
        else:
            self._finish_resolution()

    def step_resolution(self) -> None:
        if not self.resolution_active:
            return
        if not self.resolution_queue:
            self._finish_resolution()
            return

        event = self.resolution_queue.pop(0)
        self.current_resolution_event = event
        self._process_resolution_event(event)

        if not self.resolution_queue:
            self._finish_resolution()

    def _finish_resolution(self) -> None:
        self.resolution_active = False
        self.current_resolution_event = None
        mass_context = Context(game=self, target=None, slot=None, damage=0)
        self.mass_broadcast('turn_end', 'turn_end', mass_context)

        for creature in [self.playerchar] + self.enemy_list:
            if creature.is_alive():
                creature.draw_skills(1)

        self.playerchar.decay_status()
        self._recover_staggered_SR(self.playerchar)
        for enemy in self.enemy_list:
            enemy.decay_status()
            self._recover_staggered_SR(enemy)

        if self.state == GameState.COMBAT:
            if not any(e.is_alive() for e in self.enemy_list):
                self.exit_combat()
            else:
                self.begin_turn()

    def _build_resolution_queue(self) -> None:
        snapshot = sorted(self.res_order, key=lambda s: s.get_speed(), reverse=True)
        processed = set()

        for slot in snapshot:
            if id(slot) in processed:
                continue

            if slot.owner is None or not slot.owner.is_alive():
                continue

            defender = slot.get_target_creature()
            targets = self.get_skill_targets(slot)
            if not targets:
                continue

            primary_target = defender if defender and defender.is_alive() else next((t for t in targets if t.is_alive()), None)
            if primary_target is None:
                continue

            counter_slot = next(
                (s for s in snapshot
                 if s.owner == defender
                 and s.get_target_creature() == slot.owner
                 and id(s) not in processed),
                None
            )

            if slot.assigned_skill is None:
                continue
            if counter_slot is not None:
                if counter_slot.assigned_skill is None:
                    continue
                self.resolution_queue.extend(self._build_clash_sequence(slot, counter_slot, primary_target))
                processed.add(id(counter_slot))
            else:
                self.resolution_queue.extend(self._build_attack_sequence(slot, primary_target))

            processed.add(id(slot))

        self.res_order.clear()

    def _build_clash_sequence(self, slot: Skillslot, counter_slot: Skillslot, primary_target: Creature) -> list[dict]:
        attacker = slot.owner
        defender = primary_target
        skill = slot.assigned_skill
        opponent_skill = counter_slot.assigned_skill

        my_dice = [die.copy() for die in skill.dice]
        their_dice = [die.copy() for die in opponent_skill.dice]

        base_context = Context(
            game=self,
            attacker=attacker,
            defender=defender,
            target=slot.get_target_creature() or primary_target,
            skill=skill,
            opponent_skill=opponent_skill,
            slot=slot,
            opponent_slot=counter_slot,
            die=None,
            index=-1,
            clash_history=[],
            damage=0,
            targets=self.get_skill_targets(slot),
            target_positions=slot.get_target_positions()
        )

        sequence = [
            {
                'type': 'clash_start',
                'context': base_context,
                'description': f'{attacker.name} clashes with {defender.name}'
            }
        ]

        min_len = min(len(my_dice), len(their_dice))
        for idx in range(min_len):
            sequence.append({
                'type': 'clash_die',
                'index': idx,
                'context': base_context,
                'my_die': my_dice[idx],
                'their_die': their_dice[idx],
                'player_is_attacker': attacker == self.playerchar,
                'description': f'Clash roll {idx + 1}'
            })

        if len(their_dice) > min_len:
            sequence.extend(self._build_attack_sequence(counter_slot, slot.owner, start_index=min_len, use_slot=counter_slot))
        elif len(my_dice) > min_len:
            sequence.extend(self._build_attack_sequence(slot, primary_target, start_index=min_len, use_slot=slot))

        sequence.append({
            'type': 'sequence_end',
            'slot': slot,
            'counter_slot': counter_slot
        })
        return sequence

    def _build_attack_sequence(self, slot: Skillslot, primary_target: Creature, start_index: int = 0, use_slot: Skillslot | None = None) -> list[dict]:
        if use_slot is None:
            use_slot = slot
        skill = use_slot.assigned_skill
        attacker = use_slot.owner
        targets = self.get_skill_targets(use_slot)

        context = Context(
            game=self,
            attacker=attacker,
            defender=primary_target,
            target=use_slot.get_target_creature() or primary_target,
            skill=skill,
            slot=use_slot,
            die=None,
            index=-1,
            clash_history=[],
            damage=0,
            targets=targets,
            target_positions=use_slot.get_target_positions()
        )

        sequence = [
            {
                'type': 'attack_start',
                'context': context,
                'start_index': start_index,
                'player_attack': attacker == self.playerchar,
                'description': f'{attacker.name} begins an unopposed attack'
            }
        ]

        dice = [die.copy() for die in skill.dice]
        for idx in range(start_index, len(dice)):
            sequence.append({
                'type': 'attack_die',
                'index': idx,
                'context': context,
                'die': dice[idx],
                'player_attack': attacker == self.playerchar,
                'description': f'Attack roll {idx + 1}'
            })

        sequence.append({
            'type': 'sequence_end',
            'slot': use_slot,
            'counter_slot': None
        })
        return sequence

    def _process_resolution_event(self, event: dict) -> None:
        etype = event.get('type')

        match etype:
            case 'clash_start':
                context = event['context']
                context.phase = 'clash'
                context.attacker.process_effects('on_play', context)
                context.skill.process_effects('on_play', context)
                context.skill.process_effects('on_clash_start', context)

            case 'clash_die':
                context = event['context']
                context.phase = 'clash'
                context.index = event['index']
                context.skill.process_effects('on_clash', context)

                attacker = context.attacker
                defender = context.defender
                my_die = event['my_die']
                their_die = event['their_die']

                context.die = my_die
                context.attacker = attacker
                context.defender = defender
                attacker.process_effects('on_die_roll', context)
                my_die.process_effects('on_die_roll', context)
                attacker_roll = my_die.roll(context)

                context.die = their_die
                context.attacker = defender
                context.defender = attacker
                defender.process_effects('on_die_roll', context)
                their_die.process_effects('on_die_roll', context)
                defender_roll = their_die.roll(context)

                context.clash_history.append((attacker_roll, defender_roll))
                event['attacker_roll'] = attacker_roll
                event['defender_roll'] = defender_roll

                if attacker_roll > defender_roll:
                    context.damage = attacker_roll - defender_roll
                    context.die = my_die
                    context.attacker = attacker
                    context.defender = defender
                    attacker.process_effects('on_win', context)
                    my_die.process_effects('on_win', context)
                    target = context.get_opponent(attacker)
                    target.take_damage(context.damage, my_die.type, context)
                elif defender_roll > attacker_roll:
                    context.damage = defender_roll - attacker_roll
                    context.die = their_die
                    context.attacker = defender
                    context.defender = attacker
                    defender.process_effects('on_win', context)
                    their_die.process_effects('on_win', context)
                    target = context.get_opponent(defender)
                    target.take_damage(context.damage, their_die.type, context)
                else:
                    event['result'] = 'tie'

            case 'attack_start':
                context = event['context']
                context.phase = 'attack'
                context.opponent_skill = None
                context.opponent_slot = None
                context.attacker.process_effects('on_play', context)
                context.skill.process_effects('on_play', context)
                context.skill.process_effects('on_unopposed_attack', context)

            case 'attack_die':
                context = event['context']
                context.phase = 'attack'
                context.index = event['index']
                context.die = event['die']

                attacker = context.attacker
                context.attacker.process_effects('on_die_roll', context)
                context.die.process_effects('on_die_roll', context)
                roll = context.die.roll(context)
                event['roll'] = roll

                targets = context.targets or ([context.defender] if context.defender else [])
                for target in targets:
                    if target is None or not target.is_alive():
                        continue
                    target_context = context.with_target(target)
                    context.skill.process_effects('on_hit', target_context)
                    context.die.process_effects('on_hit', target_context)
                    context.die.process_effects('on_unopposed_hit', target_context)
                    target.take_damage(roll, context.die.type, target_context)

            case 'sequence_end':
                slot = event['slot']
                counter_slot = event.get('counter_slot')
                context = Context(game=self, attacker=slot.owner, defender=slot.get_target_creature() or None, skill=slot.assigned_skill, slot=slot, die=None, index=-1, clash_history=[], damage=0)
                if slot.owner:
                    slot.owner.process_effects('on_attack_end', context)
                    slot.owner.discard(slot.assigned_skill, context)
                if counter_slot is not None and counter_slot.owner:
                    counter_context = Context(game=self, attacker=counter_slot.owner, defender=counter_slot.get_target_creature() or None, skill=counter_slot.assigned_skill, slot=counter_slot, die=None, index=-1, clash_history=[], damage=0)
                    counter_slot.owner.process_effects('on_attack_end', counter_context)
                    counter_slot.owner.discard(counter_slot.assigned_skill, counter_context)

    def exit_combat(self) -> None:
        if self.combat_room is not None:
            self.floor.unlock_room(self.combat_room)
            self.combat_room.cleared = True
            self.combat_room = None
        self.res_order.clear()
        self.enemy_list = []
        self.set_state(GameState.EXPLORING)

    def encounter_found(self, room: RoomRect | None) -> list[Creature] | None:
        if room is None or room.cleared or not room.encounter_positions:
            return None
        enemies = [self.spawn_enemy_at(pos) for pos in room.encounter_positions]
        room.encounter_positions = []
        return enemies

    def spawn_enemy_at(self, pos: tuple[int, int]) -> Creature:
        enemy = self.engine.create_random_enemy(pos)
        self.add_enemy(enemy)
        return enemy
    
    def add_enemy(self, enemy: Creature) -> None:
        enemy.layout = self
        if enemy.max_points > 0:
            enemy.points = enemy.max_points
        try:
            enemy.effects.append(self.engine.load_effect('restore_points'))
        except ValueError:
            pass
        if enemy.max_points > 0:
            try:
                enemy.effects.append(self.engine.load_effect('card_draw'))
            except ValueError:
                pass
        self.apply_default_turn_end_effects(enemy)
        self.enemy_list.append(enemy)

    def get_creature_at(self, x: int, y: int) -> Optional[Creature]:
        if self.playerchar.is_alive() and self.playerchar.pos == (x, y):
            return self.playerchar
        return next((creature for creature in self.enemy_list
                     if creature.is_alive() and creature.pos == (x, y)), None)

    def get_creatures_in_positions(self, positions: list[tuple[int, int]]) -> list[Creature]:
        targets: list[Creature] = []
        for pos in positions:
            creature = self.get_creature_at(*pos)
            if creature and creature not in targets:
                targets.append(creature)
        return targets

    def get_skill_targets(self, slot: Skillslot) -> list[Creature]:
        skill = slot.get_skill()
        if skill is None:
            return []

        if slot.get_target_positions():
            return self.get_creatures_in_positions(slot.get_target_positions())

        match skill.targeting_type:
            case 'self':
                return [slot.owner] if slot.owner and slot.owner.is_alive() else []
            case 'all_enemies':
                return [enemy for enemy in self.enemy_list if enemy.is_alive()] if slot.owner == self.playerchar else ([self.playerchar] if self.playerchar.is_alive() else [])
            case 'all_allies':
                return [self.playerchar] if slot.owner == self.playerchar else [enemy for enemy in self.enemy_list if enemy.is_alive()]
            case 'enemy':
                target = slot.get_target_creature()
                return [target] if target and target.is_alive() else []
            case _:
                target = slot.get_target_creature()
                return [target] if target and target.is_alive() else []

    def add_slot(self, slot: Skillslot):
        self.res_order.append(slot)

    def get_allies(self, creature: Creature) -> list[Creature]:
        if creature is self.playerchar:
            return [self.playerchar]
        return [ally for ally in self.enemy_list if ally.is_alive()]
    
    def mass_broadcast(self, trigger: str, phase: str, context: 'Context') -> None:
        context.phase = phase

        context.actor = self.playerchar
        context.attacker = self.playerchar
        self.playerchar.process_effects(trigger, context)

        for enemy in self.enemy_list:
            if not enemy.is_alive():
                continue
            
            context.actor = enemy
            context.attacker = enemy
            enemy.process_effects(trigger, context)

    def broadcast_ally_effects(self, creature: Creature, trigger: str, context: 'Context') -> None:
        for ally in self.get_allies(creature):
            if ally is not creature:
                ally.process_effects(trigger, context)

    def handle_death(self, creature: Creature, context: 'Context' = None) -> None:
        if creature is self.playerchar:
            self.end()
        else:
            if context:
                self.broadcast_ally_effects(creature, 'on_ally_death', context)
            to_remove = [s for s in self.res_order 
                        if s.owner == creature or s.target == creature]
            for slot in to_remove:
                self.res_order.remove(slot)
            if creature in self.enemy_list:
                self.enemy_list.remove(creature)
    
    def handle_stagger(self, creature: Creature, context: 'Context' = None) -> None:
        if context:
            self.broadcast_ally_effects(creature, 'on_ally_stagger', context)
            to_remove = [s for s in self.res_order 
                        if s.owner == creature]
            for slot in to_remove:
                self.res_order.remove(slot)
            self._remove_staggered_resolution_events(creature)

    def _event_belongs_to_creature(self, event: dict, creature: Creature) -> bool:
        if event.get('slot') and event['slot'].owner is creature:
            return True
        if event.get('counter_slot') and event['counter_slot'].owner is creature:
            return True
        context = event.get('context')
        if context is None:
            return False
        return context.attacker is creature or context.defender is creature or context.target is creature

    def _remove_staggered_resolution_events(self, creature: Creature) -> None:
        self.resolution_queue = [event for event in self.resolution_queue
                                 if not self._event_belongs_to_creature(event, creature)]

    def _recover_staggered_SR(self, creature: Creature) -> None:
        if creature.is_staggered():
            creature.staggered_turns += 1
            if creature.staggered_turns > 1:
                creature.SR = creature.max_SR
                creature.staggered_turns = 0

    def end(self):
        if self.combat_room is not None:
            self.floor.unlock_room(self.combat_room)
            self.combat_room = None
        self.enemy_list.clear()
        self.res_order.clear()
        self.set_state(GameState.GAME_OVER)