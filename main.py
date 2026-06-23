import sys
import random
from typing import Optional

import pygame
from pygame import Vector2

from config import WIDTH, HEIGHT, FPS, COLOR_BG, TILE_SIZE
from creature import Creature
from engine import Engine
from game import Game, GameState
from skillslot import Skillslot

CARD_WIDTH = 180
CARD_HEIGHT = 120
SLOT_HEIGHT = 100
SLOT_WIDTH = 180
HAND_BUTTON_RECT = pygame.Rect(WIDTH - 170, HEIGHT - 160, 160, 45)
SLOTS_BUTTON_RECT = pygame.Rect(WIDTH - 170, HEIGHT - 110, 160, 45)
END_BUTTON_RECT = pygame.Rect(WIDTH - 170, HEIGHT - 60, 160, 45)
PLAYER_STATUS_BUTTON_RECT = pygame.Rect(420, 10, 100, 24)
OVERWORLD_HUD_RECT = pygame.Rect(10, 10, 360, 58)
OVERWORLD_DECK_BUTTON_RECT = pygame.Rect(18, 46, 90, 28)
OVERWORLD_HAND_BUTTON_RECT = pygame.Rect(114, 46, 90, 28)
OVERWORLD_DISCARD_BUTTON_RECT = pygame.Rect(210, 46, 140, 28)


def draw_text(surface, text, position, font, color=(255, 255, 255)):
    if not text:
        return
    lines = text.split('\n')
    for index, line in enumerate(lines):
        surface.blit(font.render(line, True, color), (position[0], position[1] + index * (font.get_height() + 2)))


def wrap_text(text: str, font, max_width: int) -> list[str]:
    words = text.split(' ')
    lines: list[str] = []
    current = ''
    for word in words:
        test = f'{current} {word}' if current else word
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def build_card_text_lines(card, font_small) -> list[str]:
    lines = wrap_text(card.description or 'No description', font_small, CARD_WIDTH - 16)
    effect_lines: list[str] = []
    if getattr(card, 'effects', None):
        effect_lines.append('Effects:')
        for effect in card.effects:
            effect_lines.extend(wrap_text(effect.describe(), font_small, CARD_WIDTH - 16))

    for die in card.dice:
        if getattr(die, 'effects', None) and die.effects:
            effect_lines.append(f'{die.type.capitalize()} die effects:')
            for effect in die.effects:
                effect_lines.extend(wrap_text(effect.describe(), font_small, CARD_WIDTH - 16))

    if effect_lines:
        lines.append('')
        lines.extend(effect_lines)
    return lines


def clamp_hand_scroll(hand: list[object], offset: int) -> int:
    base_x = 10
    spacing = CARD_WIDTH + 10
    total_width = base_x + len(hand) * spacing
    min_offset = min(0, WIDTH - total_width)
    return max(min_offset, min(0, offset))


def create_player_slots(owner: Creature) -> list[Skillslot]:
    slots = []
    for _ in range(3):
        slot = Skillslot(speed_range=(1, 7))
        slot.owner = owner
        slot.roll_speed()
        slots.append(slot)
    return slots


def get_slot_rects(slots: list[Skillslot], hand_visible: bool) -> list[tuple[Skillslot, pygame.Rect]]:
    rects = []
    base_x = 10
    if hand_visible:
        base_y = HEIGHT - 220
    else:
        base_y = HEIGHT - SLOT_HEIGHT - 10
    spacing = SLOT_WIDTH + 10
    for index, slot in enumerate(slots):
        rect = pygame.Rect(base_x + index * spacing, base_y, SLOT_WIDTH, SLOT_HEIGHT)
        rects.append((slot, rect))
    return rects


def get_card_rects(hand: list[object], scroll_x: int = 0) -> list[tuple[object, pygame.Rect]]:
    rects = []
    base_x = 10
    base_y = HEIGHT - 110
    spacing = CARD_WIDTH + 10
    for index, card in enumerate(hand):
        rect = pygame.Rect(base_x + index * spacing + scroll_x, base_y, CARD_WIDTH, CARD_HEIGHT)
        rects.append((card, rect))
    return rects


def get_camera_offset(game: Game) -> tuple[int, int]:
    positions = [Vector2(game.playerchar.pos[0] * TILE_SIZE + TILE_SIZE / 2,
                         game.playerchar.pos[1] * TILE_SIZE + TILE_SIZE / 2)]
    positions += [Vector2(enemy.pos[0] * TILE_SIZE + TILE_SIZE / 2,
                          enemy.pos[1] * TILE_SIZE + TILE_SIZE / 2)
                  for enemy in game.enemy_list if enemy.is_alive()]
    if positions:
        center_pos = sum(positions, Vector2(0, 0)) / len(positions)
    else:
        center_pos = Vector2(WIDTH / 2, HEIGHT / 2)
    return (int(WIDTH / 2 - center_pos.x), int(HEIGHT / 2 - center_pos.y))


def get_enemy_rects(enemies: list[Creature], offset: tuple[int, int] = (0, 0)) -> list[tuple[Creature, pygame.Rect, tuple[int, int]]]:
    rects = []
    for enemy in enemies:
        center = (enemy.pos[0] * TILE_SIZE + TILE_SIZE // 2 + offset[0],
                  enemy.pos[1] * TILE_SIZE + TILE_SIZE // 2 + offset[1])
        rect = pygame.Rect(center[0] - 24, center[1] - 24, 48, 48)
        rects.append((enemy, rect, center))
    return rects


def draw_card(surface, card, rect, font_small, font_medium, text_scroll: int = 0):
    pygame.draw.rect(surface, (40, 40, 60), rect)
    pygame.draw.rect(surface, (160, 160, 220), rect, 2)
    draw_text(surface, card.name, (rect.x + 8, rect.y + 8), font_medium)
    draw_text(surface, f'Cost: {card.cost}', (rect.x + 8, rect.y + 30), font_small)

    line_height = font_small.get_height() + 2
    desc_y = rect.y + 48
    available_height = rect.height - 48 - line_height - 12
    max_desc_lines = max(1, available_height // line_height)

    content_lines = build_card_text_lines(card, font_small)
    start_line = max(0, min(text_scroll, max(0, len(content_lines) - max_desc_lines)))
    for i in range(max_desc_lines):
        if start_line + i >= len(content_lines):
            break
        draw_text(surface, content_lines[start_line + i], (rect.x + 8, desc_y + i * line_height), font_small)

    dice_lines = []
    for die in card.dice:
        dice_lines.append(f'{die.type} {die.min_roll}-{die.max_roll}')
    dice_text = ' | '.join(dice_lines) if dice_lines else 'No dice'
    dice_lines_wrapped = wrap_text(dice_text, font_small, rect.width - 16)
    dice_y = rect.y + rect.height - line_height - 8
    if dice_lines_wrapped:
        draw_text(surface, dice_lines_wrapped[0], (rect.x + 8, dice_y), font_small)

    if len(content_lines) > max_desc_lines:
        indicator = f'{start_line + 1}-{min(start_line + max_desc_lines, len(content_lines))}/{len(content_lines)}'
        draw_text(surface, indicator, (rect.right - 10 - font_small.size(indicator)[0], rect.y + rect.height - line_height - 8), font_small, (200, 200, 160))


def draw_overworld_skill_list(surface, items: list, font_small, font_medium, x: int, y: int):
    if not items:
        text = 'None'
        draw_text(surface, text, (x, y), font_small)
        return

    row_y = y
    for item in items:
        box = pygame.Rect(x, row_y, 320, 26)
        pygame.draw.rect(surface, (35, 35, 55), box)
        pygame.draw.rect(surface, (140, 140, 170), box, 1)
        draw_text(surface, f'{item.name} ({item.cost})', (box.x + 6, box.y + 5), font_small)
        row_y += 30


def draw_overworld_skill_popup(surface, card, font_small, font_medium, x: int, y: int):
    content_lines = build_card_text_lines(card, font_small)
    line_height = font_small.get_height() + 2
    panel_width = 320
    panel_padding = 10
    content_height = max(1, len(content_lines)) * line_height
    panel_height = min(360, content_height + panel_padding * 6)
    popup = pygame.Rect(x, y, panel_width, panel_height)
    pygame.draw.rect(surface, (28, 28, 44), popup)
    pygame.draw.rect(surface, (210, 210, 240), popup, 2)
    title_y = popup.y + 8
    draw_text(surface, card.name, (popup.x + 8, title_y), font_medium)
    draw_text(surface, f'Cost: {card.cost}', (popup.x + 8, title_y + 24), font_small)

    start_y = title_y + 46
    for line in content_lines:
        draw_text(surface, line, (popup.x + 8, start_y), font_small)
        start_y += line_height


def draw_enemy_details(surface, game: 'Game', enemy: Creature, font_small, font_medium, font_large):
    panel = pygame.Rect(WIDTH - 260, 10, 250, 300)
    pygame.draw.rect(surface, (24, 24, 40), panel)
    pygame.draw.rect(surface, (210, 210, 230), panel, 2)
    draw_text(surface, enemy.name, (panel.x + 10, panel.y + 10), font_large)
    draw_text(surface, f'HP: {max(0, enemy.HP)}/{enemy.max_HP}', (panel.x + 10, panel.y + 40), font_medium)
    draw_text(surface, f'SR: {enemy.SR}', (panel.x + 10, panel.y + 62), font_medium)

    draw_text(surface, 'Statuses:', (panel.x + 10, panel.y + 90), font_medium)
    status_y = panel.y + 112
    if enemy.statuses:
        for status in enemy.statuses.values():
            draw_text(surface, f'{status.name} ({status.potency}/{status.count})', (panel.x + 10, status_y), font_small)
            status_y += font_small.get_height() + 2
            for line in wrap_text(status.description or '', font_small, panel.width - 20):
                draw_text(surface, line, (panel.x + 12, status_y), font_small)
                status_y += font_small.get_height() + 2
            status_y += 4
    else:
        draw_text(surface, 'None', (panel.x + 10, status_y), font_small)

    slot_y = status_y + font_small.get_height() + 8
    draw_text(surface, 'Planned actions:', (panel.x + 10, slot_y), font_medium)
    slot_y += font_small.get_height() + 4
    enemy_slots = [slot for slot in game.res_order if slot.owner == enemy]
    if enemy_slots:
        for slot in enemy_slots:
            skill_name = slot.assigned_skill.name if slot.assigned_skill else 'Empty'
            target_name = slot.get_target_creature().name if slot.get_target_creature() else 'None'
            draw_text(surface, f'{skill_name} ({slot.get_speed()}) -> {target_name}', (panel.x + 10, slot_y), font_small)
            slot_y += font_small.get_height() + 2
    else:
        draw_text(surface, 'None', (panel.x + 10, slot_y), font_small)


def draw_resolution_overlay(surface, game: Game, font_small, font_medium, font_large):
    event = game.current_resolution_event
    if not event:
        return

    box_size = 72
    left_box = pygame.Rect(WIDTH // 2 - box_size - 8, 60, box_size, box_size)
    right_box = pygame.Rect(WIDTH // 2 + 8, 60, box_size, box_size)
    pygame.draw.rect(surface, (0, 0, 0), left_box)
    pygame.draw.rect(surface, (0, 0, 0), right_box)
    pygame.draw.rect(surface, (140, 140, 140), left_box, 2)
    pygame.draw.rect(surface, (140, 140, 140), right_box, 2)

    left_value = ''
    right_value = ''
    description = event.get('description', '')
    match event['type']:
        case 'clash_die':
            if event.get('player_is_attacker'):
                left_value = str(event.get('attacker_roll', ''))
                right_value = str(event.get('defender_roll', ''))
            else:
                left_value = str(event.get('defender_roll', ''))
                right_value = str(event.get('attacker_roll', ''))

        case 'attack_die':
            roll = str(event.get('roll', ''))
            if event.get('player_attack'):
                left_value = roll
                right_value = '-'
            else:
                left_value = '-'
                right_value = roll
        case _:
            pass

    text = description if description else ''
    if text:
        text_lines = wrap_text(text, font_small, box_size * 2 + 16)
        bg_height = len(text_lines) * (font_small.get_height() + 2) + 8
        bg_rect = pygame.Rect(WIDTH // 2 - box_size - 16, left_box.y - bg_height - 10, (box_size * 2) + 16, bg_height)
        pygame.draw.rect(surface, (0, 0, 0), bg_rect)
        pygame.draw.rect(surface, (140, 140, 140), bg_rect, 1)
        line_y = bg_rect.y + 4
        for line in text_lines:
            line_x = bg_rect.x + 8
            draw_text(surface, line, (line_x, line_y), font_small, (255, 255, 255))
            line_y += font_small.get_height() + 2

    draw_text(surface, left_value, (left_box.centerx - font_large.size(left_value)[0] // 2, left_box.centery - 8), font_large)
    draw_text(surface, right_value, (right_box.centerx - font_large.size(right_value)[0] // 2, right_box.centery - 8), font_large)


def draw_combat(surface, game: Game, player_slots: list[Skillslot], selected_slot: Skillslot | None,
                selected_card, selected_enemy: Creature | None, hand_scroll_x: int,
                card_text_scroll: dict[int, int], font_small, font_medium, font_large, message: str,
                hand_visible: bool, slots_visible: bool, show_player_statuses: bool, offset: tuple[int, int]):
    surface.fill((18, 18, 28))
    game.draw_floor(surface, offset)

    enemy_rects = []
    for enemy in game.enemy_list:
        center = (enemy.pos[0] * TILE_SIZE + TILE_SIZE // 2 + offset[0],
                  enemy.pos[1] * TILE_SIZE + TILE_SIZE // 2 + offset[1])
        rect = pygame.Rect(center[0] - 24, center[1] - 24, 48, 48)
        enemy_rects.append((enemy, rect, center))
    for enemy, rect, center in enemy_rects:
        color = (200, 80, 80) if enemy.is_alive() else (80, 80, 80)
        pygame.draw.circle(surface, color, center, 24)
        draw_text(surface, enemy.name, (center[0] - 30, center[1] - 50), font_small)
        if selected_enemy is enemy:
            hp_text = f'HP: {max(0, enemy.HP)}/{enemy.max_HP} SR: {enemy.SR}'
            draw_text(surface, hp_text, (center[0] - 42, center[1] + 30), font_small)

    player_center = (game.playerchar.pos[0] * TILE_SIZE + TILE_SIZE // 2 + offset[0],
                     game.playerchar.pos[1] * TILE_SIZE + TILE_SIZE // 2 + offset[1])
    pygame.draw.circle(surface, (255, 50, 50), player_center, TILE_SIZE // 3)

    if selected_enemy is not None:
        for slot in game.res_order:
            if slot.owner != game.playerchar and slot.owner == selected_enemy:
                target = slot.get_target_creature()
                if target and target.is_alive():
                    start = (slot.owner.pos[0] * TILE_SIZE + TILE_SIZE // 2 + offset[0], slot.owner.pos[1] * TILE_SIZE + TILE_SIZE // 2 + offset[1])
                    end = (target.pos[0] * TILE_SIZE + TILE_SIZE // 2 + offset[0], target.pos[1] * TILE_SIZE + TILE_SIZE // 2 + offset[1])
                    pygame.draw.line(surface, (220, 200, 80), start, end, 3)

        for enemy, rect, center in enemy_rects:
            if enemy is selected_enemy:
                enemy_slots = [slot for slot in game.res_order if slot.owner == enemy]
                for idx, slot in enumerate(enemy_slots[:2]):
                    slot_box = pygame.Rect(center[0] - 42, center[1] - 52 - idx * 26, 84, 22)
                    pygame.draw.rect(surface, (50, 50, 80), slot_box)
                    pygame.draw.rect(surface, (230, 230, 120), slot_box, 2)
                    text = f'{slot.assigned_skill.name if slot.assigned_skill else "???"} {slot.get_speed()}'
                    draw_text(surface, text, (slot_box.x + 4, slot_box.y + 2), font_small)

        draw_enemy_details(surface, game, selected_enemy, font_small, font_medium, font_large)
    else:
        for slot in game.res_order:
            if slot.owner != game.playerchar and slot.owner in game.enemy_list:
                target = slot.get_target_creature()
                if target and target.is_alive():
                    start = (slot.owner.pos[0] * TILE_SIZE + TILE_SIZE // 2 + offset[0], slot.owner.pos[1] * TILE_SIZE + TILE_SIZE // 2 + offset[1])
                    end = (target.pos[0] * TILE_SIZE + TILE_SIZE // 2 + offset[0], target.pos[1] * TILE_SIZE + TILE_SIZE // 2 + offset[1])
                    pygame.draw.line(surface, (220, 200, 80), start, end, 3)

    stats_text = f'HP: {game.playerchar.HP}/{game.playerchar.max_HP}  SR: {game.playerchar.SR}  Shield: {game.playerchar.shield}  Points: {game.playerchar.points}/{game.playerchar.max_points}'
    menu_height = 64
    if show_player_statuses:
        if game.playerchar.statuses:
            menu_height = 90 + len(game.playerchar.statuses) * (font_small.get_height() + 2)
        else:
            menu_height = 90
    menu_box = pygame.Rect(6, 6, 440, menu_height)
    pygame.draw.rect(surface, (20, 20, 20), menu_box)
    pygame.draw.rect(surface, (150, 150, 150), menu_box, 2)

    draw_text(surface, stats_text, (menu_box.x + 8, menu_box.y + 8), font_medium)
    pygame.draw.rect(surface, (35, 35, 55), PLAYER_STATUS_BUTTON_RECT)
    pygame.draw.rect(surface, (200, 200, 220), PLAYER_STATUS_BUTTON_RECT, 2)
    draw_text(surface, ('Status' if not show_player_statuses else 'Hide'), (PLAYER_STATUS_BUTTON_RECT.x + 12, PLAYER_STATUS_BUTTON_RECT.y + 4), font_small)

    if show_player_statuses:
        status_y = menu_box.y + 36
        if game.playerchar.statuses:
            draw_text(surface, 'Statuses:', (menu_box.x + 8, status_y), font_small)
            status_y += font_small.get_height() + 4
            for status in game.playerchar.statuses.values():
                draw_text(surface, f'{status.name} ({status.potency}/{status.count})', (menu_box.x + 12, status_y), font_small)
                status_y += font_small.get_height() + 2
        else:
            draw_text(surface, 'No statuses', (menu_box.x + 8, status_y), font_small)

    draw_text(surface, 'Click slot -> click card -> drag slot to enemy -> End Turn', (10, menu_box.bottom + 6), font_small, (200, 190, 220))
    draw_text(surface, message, (10, menu_box.bottom + 26), font_small, (180, 220, 180))

    for number in game.damage_numbers:
        text_width = font_medium.size(number['text'])[0]
        draw_text(surface, number['text'], (number['x'] - text_width // 2 + offset[0], number['y'] + offset[1]), font_medium, number['color'])

    for number in game.status_numbers:
        text_width = font_medium.size(number['text'])[0]
        draw_text(surface, number['text'], (number['x'] - text_width // 2 + offset[0], number['y'] + offset[1]), font_medium, number['color'])

    game.draw_attack_animations(surface, offset)

    if game.resolution_active:
        draw_resolution_overlay(surface, game, font_small, font_medium, font_large)

    pygame.draw.rect(surface, (80, 80, 120), HAND_BUTTON_RECT)
    pygame.draw.rect(surface, (240, 240, 240), HAND_BUTTON_RECT, 2)
    draw_text(surface, ('Hide Hand' if hand_visible else 'Show Hand'), (HAND_BUTTON_RECT.x + 16, HAND_BUTTON_RECT.y + 12), font_small)

    if not hand_visible:
        pygame.draw.rect(surface, (80, 80, 120), SLOTS_BUTTON_RECT)
        pygame.draw.rect(surface, (240, 240, 240), SLOTS_BUTTON_RECT, 2)
        draw_text(surface, ('Hide Slots' if slots_visible else 'Show Slots'), (SLOTS_BUTTON_RECT.x + 14, SLOTS_BUTTON_RECT.y + 12), font_small)

    slot_rects = get_slot_rects(player_slots, hand_visible) if slots_visible else []
    for slot, rect in slot_rects:
        fill = (100, 100, 140) if slot is selected_slot else (50, 50, 80)
        pygame.draw.rect(surface, fill, rect)
        pygame.draw.rect(surface, (240, 240, 240), rect, 2)
        label = slot.assigned_skill.name if slot.assigned_skill else 'Empty slot'
        draw_text(surface, label, (rect.x + 8, rect.y + 8), font_medium)
        draw_text(surface, f'Speed: {slot.get_speed()}', (rect.x + 8, rect.y + 32), font_small)
        draw_text(surface, f'Target: {slot.get_target_creature().name if slot.get_target_creature() else "None"}', (rect.x + 8, rect.y + 50), font_small)

        if slot.get_target_creature():
            position = (rect.centerx, rect.centery)
            target = slot.get_target_creature()
            enemy_center = (target.pos[0] * TILE_SIZE + TILE_SIZE // 2 + offset[0],
                            target.pos[1] * TILE_SIZE + TILE_SIZE // 2 + offset[1])
            pygame.draw.line(surface, (130, 220, 130), position, enemy_center, 3)
    card_rects = get_card_rects(game.playerchar.hand, hand_scroll_x) if hand_visible else []
    for card, rect in card_rects:
        draw_card(surface, card, rect, font_small, font_medium, card_text_scroll.get(id(card), 0))
        if selected_card == card:
            pygame.draw.rect(surface, (220, 220, 100), rect, 3)

    pygame.draw.rect(surface, (50, 130, 50), END_BUTTON_RECT)
    pygame.draw.rect(surface, (240, 240, 240), END_BUTTON_RECT, 2)
    draw_text(surface, 'End Turn', (END_BUTTON_RECT.x + 38, END_BUTTON_RECT.y + 12), font_medium)


def run_menu_system() -> tuple[bool, Optional[Creature]]:
    from menu_manager import MenuManager
    
    menu_manager = MenuManager()
    clock = pygame.time.Clock()
    
    while menu_manager.is_running():
        dt = clock.tick(FPS) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False, None
            menu_manager.handle_event(event)
        
        menu_manager.update(dt)
        
        screen = pygame.display.get_surface()
        menu_manager.draw(screen)
        pygame.display.flip()
    
    if menu_manager.should_exit_game():
        return False, None
    
    if menu_manager.should_play():
        player = Creature('Hero', 'A nimble adventurer', 30, 5, {}, [], [], max_points=3)
        engine = Engine()
        player.deck = [engine.load_skill(skill_id) for skill_id in engine.get_random_skill_ids(8)]
        random.shuffle(player.deck)
        player.draw_skills(5)
        player.points = player.max_points
        return True, player
    
    return False, None


def main() -> None:
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption('Dice Combat Dungeon')
    clock = pygame.time.Clock()
    font_small = pygame.font.Font(None, 18)
    font_medium = pygame.font.Font(None, 20)
    font_large = pygame.font.Font(None, 24)

    # Run menu system first
    should_play, player = run_menu_system()
    
    if not should_play or player is None:
        pygame.quit()
        sys.exit(0)
    
    # Setup game
    engine = Engine()
    game = Game(player, engine=engine)

    player_slots = create_player_slots(player)
    selected_slot = None
    selected_card = None
    selected_enemy = None
    dragging_slot = None
    hand_scroll_x = 0
    card_text_scroll: dict[int, int] = {}
    hand_visible = True
    slots_visible = True
    show_player_statuses = False
    overworld_list_mode = None
    overworld_selected_skill = None
    last_slot_click_time = 0
    last_slot_clicked = None
    resolution_last_step = pygame.time.get_ticks()
    message = 'Explore the dungeon. Enter a room to fight.'
    previous_resolution_active = False

    running = True
    while running:
        offset = get_camera_offset(game)
        slot_rects = get_slot_rects(player_slots, hand_visible) if slots_visible else []
        card_rects = get_card_rects(player.hand, hand_scroll_x) if hand_visible else []
        enemy_rects = get_enemy_rects(game.enemy_list, offset)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN and game.state == GameState.EXPLORING:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_LEFT:
                    game.move_player(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    game.move_player(1, 0)
                elif event.key == pygame.K_UP:
                    game.move_player(0, -1)
                elif event.key == pygame.K_DOWN:
                    game.move_player(0, 1)

                if game.state == GameState.COMBAT:
                    message = 'Combat started! Assign card slots and target enemies.'
                    player_slots = create_player_slots(player)
                    selected_slot = None
                    selected_card = None
                    dragging_slot = None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos
                    if game.state == GameState.EXPLORING:
                        if OVERWORLD_DECK_BUTTON_RECT.collidepoint(mouse_pos):
                            overworld_list_mode = None if overworld_list_mode == 'deck' else 'deck'
                            overworld_selected_skill = None
                            continue
                        if OVERWORLD_HAND_BUTTON_RECT.collidepoint(mouse_pos):
                            overworld_list_mode = None if overworld_list_mode == 'hand' else 'hand'
                            overworld_selected_skill = None
                            continue
                        if OVERWORLD_DISCARD_BUTTON_RECT.collidepoint(mouse_pos):
                            overworld_list_mode = None if overworld_list_mode == 'discarded' else 'discarded'
                            overworld_selected_skill = None
                            continue

                        if overworld_list_mode:
                            list_items = []
                            if overworld_list_mode == 'deck':
                                list_items = game.playerchar.deck
                            elif overworld_list_mode == 'hand':
                                list_items = game.playerchar.hand
                            elif overworld_list_mode == 'discarded':
                                list_items = game.playerchar.discarded

                            if list_items:
                                x = OVERWORLD_HUD_RECT.x + 8
                                y = OVERWORLD_HUD_RECT.bottom + 8
                                for index, item in enumerate(list_items):
                                    item_rect = pygame.Rect(x, y + index * 30, 320, 26)
                                    if item_rect.collidepoint(mouse_pos):
                                        overworld_selected_skill = item
                                        break
                                else:
                                    overworld_selected_skill = None
                            continue
                    elif game.state == GameState.COMBAT:
                        if HAND_BUTTON_RECT.collidepoint(mouse_pos):
                            hand_visible = not hand_visible
                            continue
                        if (not hand_visible) and SLOTS_BUTTON_RECT.collidepoint(mouse_pos):
                            slots_visible = not slots_visible
                            continue
                        if PLAYER_STATUS_BUTTON_RECT.collidepoint(mouse_pos):
                            show_player_statuses = not show_player_statuses
                            continue

                        if game.resolution_active:
                            continue

                        clicked_enemy = None
                        for enemy, rect, _ in enemy_rects:
                            if rect.collidepoint(mouse_pos):
                                clicked_enemy = enemy
                                break

                        if clicked_enemy is not None:
                            selected_enemy = clicked_enemy
                            message = f'Selected {clicked_enemy.name}. Click elsewhere to hide.'
                            continue

                        selected_enemy = None

                        if END_BUTTON_RECT.collidepoint(mouse_pos):
                            if any(slot.assigned_skill for slot in player_slots) or game.playerchar.is_staggered():
                                for slot in player_slots:
                                    if slot.assigned_skill:
                                        if slot.assigned_skill.targeting_type == 'enemy' and slot.get_target_creature() is None:
                                            continue
                                        game.add_slot(slot)
                                game.execute_turn()
                                selected_slot = None
                                selected_card = None
                                dragging_slot = None
                                if game.state == GameState.EXPLORING:
                                    message = 'Victory! Continue exploring the dungeon.'
                                else:
                                    message = 'Enemy turn resolved. Assign your next actions.'
                            else:
                                message = 'Assign at least one skill before ending the turn.'
                            continue

                        if game.playerchar.is_staggered():
                            message = 'Player is staggered and skips action selection.'
                            continue

                        for slot, rect in slot_rects:
                            if rect.collidepoint(mouse_pos):
                                click_time = pygame.time.get_ticks()
                                if slot is last_slot_clicked and click_time - last_slot_click_time <= 400:
                                    if slot.assigned_skill:
                                        player.points += slot.assigned_skill.cost
                                    slot.assigned_skill = None
                                    slot.target = None
                                    if selected_slot is slot:
                                        selected_slot = None
                                    selected_card = None
                                    message = 'Skill unassigned from slot.'
                                    last_slot_clicked = None
                                    last_slot_click_time = 0
                                    break
                                last_slot_clicked = slot
                                last_slot_click_time = click_time
                                selected_slot = slot
                                dragging_slot = slot
                                message = f'Slot selected. Pick a card for this slot.'
                                break

                        for card, rect in card_rects:
                            if rect.collidepoint(mouse_pos):
                                if selected_slot is not None:
                                    if any(s.assigned_skill == card and s is not selected_slot for s in player_slots):
                                        message = 'This card is already assigned to another slot.'
                                    else:
                                        old_skill = selected_slot.assigned_skill
                                        old_cost = old_skill.cost if old_skill else 0
                                        available_points = player.points + old_cost
                                        if available_points >= card.cost:
                                            if old_skill:
                                                player.points += old_cost
                                            selected_slot.assigned_skill = card
                                            player.points -= card.cost
                                            selected_card = card
                                            selected_slot = None
                                            message = f'Assigned {card.name} to the selected slot.'
                                        else:
                                            message = 'Not enough points to assign that card.'
                                    break
                                else:
                                    selected_card = card if selected_card != card else None
                                    message = f'{"Selected" if selected_card else "Deselected"} {card.name}.'
                                    break

            elif event.type == pygame.MOUSEWHEEL and game.state == GameState.COMBAT:
                mouse_pos = pygame.mouse.get_pos()
                hovered_card = None
                for card, rect in card_rects:
                    if rect.collidepoint(mouse_pos):
                        hovered_card = card
                        break

                if hovered_card is not None and hovered_card == selected_card:
                    content_lines = build_card_text_lines(hovered_card, font_small)
                    line_height = font_small.get_height() + 2
                    visible_lines = max(1, (CARD_HEIGHT - 48 - line_height - 12) // line_height)
                    max_scroll = max(0, len(content_lines) - visible_lines)
                    current_offset = card_text_scroll.get(id(hovered_card), 0)
                    card_text_scroll[id(hovered_card)] = max(0, min(max_scroll, current_offset - event.y))
                elif hovered_card is not None:
                    hand_scroll_x = clamp_hand_scroll(game.playerchar.hand, hand_scroll_x + event.y * 40)
                else:
                    hand_scroll_x = clamp_hand_scroll(game.playerchar.hand, hand_scroll_x + event.y * 40)

            elif event.type == pygame.MOUSEBUTTONUP and game.state == GameState.COMBAT:
                if game.resolution_active:
                    continue
                if event.button == 1 and dragging_slot is not None:
                    mouse_pos = event.pos
                    for enemy, rect, center in enemy_rects:
                        if rect.collidepoint(mouse_pos) and dragging_slot.assigned_skill is not None:
                            dragging_slot.set_target_creature(enemy)
                            message = f'{dragging_slot.assigned_skill.name} now targets {enemy.name}.'
                            break
                    dragging_slot = None

        if previous_resolution_active and not game.resolution_active and game.state == GameState.COMBAT:
            for slot in player_slots:
                slot.roll_speed()
                slot.assigned_skill = None
                slot.target = None
            selected_slot = None
            selected_card = None
            dragging_slot = None

        previous_resolution_active = game.resolution_active

        now = pygame.time.get_ticks()
        if game.state == GameState.COMBAT and not game.resolution_active and game.playerchar.is_staggered() and any(slot.owner != game.playerchar for slot in game.res_order):
            message = 'Player is staggered. Skipping their selection phase.'
            game.execute_turn()

        if game.resolution_active and (game.current_resolution_event is None or now - resolution_last_step >= 1000):
            game.step_resolution()
            resolution_last_step = now

        if game.state == GameState.EXPLORING:
            screen.fill(COLOR_BG)
            game.draw_floor(screen)
            player_pixel = Vector2(game.playerchar.pos[0] * TILE_SIZE + TILE_SIZE / 2,
                                   game.playerchar.pos[1] * TILE_SIZE + TILE_SIZE / 2)
            pygame.draw.circle(screen, (255, 50, 50), player_pixel, TILE_SIZE // 3)

            pygame.draw.rect(screen, (18, 18, 28), OVERWORLD_HUD_RECT)
            pygame.draw.rect(screen, (150, 150, 150), OVERWORLD_HUD_RECT, 2)
            draw_text(screen, f'HP: {game.playerchar.HP}/{game.playerchar.max_HP}   SR: {game.playerchar.SR}', (OVERWORLD_HUD_RECT.x + 8, OVERWORLD_HUD_RECT.y + 8), font_medium)

            for rect, label in [
                (OVERWORLD_DECK_BUTTON_RECT, 'Deck'),
                (OVERWORLD_HAND_BUTTON_RECT, 'Hand'),
                (OVERWORLD_DISCARD_BUTTON_RECT, 'Discarded'),
            ]:
                fill = (50, 50, 80) if overworld_list_mode == label.lower() else (35, 35, 55)
                pygame.draw.rect(screen, fill, rect)
                pygame.draw.rect(screen, (200, 200, 220), rect, 2)
                draw_text(screen, label, (rect.x + 10, rect.y + 6), font_small)

            if overworld_list_mode == 'deck':
                draw_overworld_skill_list(screen, game.playerchar.deck, font_small, font_medium, OVERWORLD_HUD_RECT.x + 8, OVERWORLD_HUD_RECT.bottom + 8)
                if overworld_selected_skill is not None:
                    draw_overworld_skill_popup(screen, overworld_selected_skill, font_small, font_medium, OVERWORLD_HUD_RECT.x + 340, OVERWORLD_HUD_RECT.bottom + 8)
            elif overworld_list_mode == 'hand':
                draw_overworld_skill_list(screen, game.playerchar.hand, font_small, font_medium, OVERWORLD_HUD_RECT.x + 8, OVERWORLD_HUD_RECT.bottom + 8)
                if overworld_selected_skill is not None:
                    draw_overworld_skill_popup(screen, overworld_selected_skill, font_small, font_medium, OVERWORLD_HUD_RECT.x + 340, OVERWORLD_HUD_RECT.bottom + 8)
            elif overworld_list_mode == 'discarded':
                draw_overworld_skill_list(screen, game.playerchar.discarded, font_small, font_medium, OVERWORLD_HUD_RECT.x + 8, OVERWORLD_HUD_RECT.bottom + 8)
                if overworld_selected_skill is not None:
                    draw_overworld_skill_popup(screen, overworld_selected_skill, font_small, font_medium, OVERWORLD_HUD_RECT.x + 340, OVERWORLD_HUD_RECT.bottom + 8)

            draw_text(screen, 'Explore with arrow keys. Enter a room to start combat.', (10, OVERWORLD_HUD_RECT.bottom + 120), font_medium)
        else:
            offset = get_camera_offset(game)
            draw_combat(screen, game, player_slots, selected_slot, selected_card, selected_enemy, hand_scroll_x, card_text_scroll, font_small, font_medium, font_large, message, hand_visible, slots_visible, show_player_statuses, offset)

        pygame.display.flip()
        dt = clock.tick(FPS)
        game.update_damage_numbers(dt)
        game.update_attack_animations(dt)

    pygame.quit()
    sys.exit(0)


if __name__ == '__main__':
    main()
