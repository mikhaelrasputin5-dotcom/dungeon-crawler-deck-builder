import pygame
import json
from pathlib import Path
from typing import Optional, Any
from enum import Enum, auto

from menu import (
    MenuState, Button, TextInput, ScrollableList, Checkbox, NumberInput,
    draw_text, create_button
)
from config import WIDTH, HEIGHT, COLOR_BG
from effect import Effect
from status import Status
from die import Die
from skill import Skill
from creature import Creature
from skillslot import Skillslot
from advanced_builders import EffectBuilderScreen, DieBuilderScreen
from pickers import SkillPickerScreen, StatusPickerScreen


class MenuScreen:
    def __init__(self, state: MenuState, go_back_callback=None):
        self.state = state
        self.go_back_callback = go_back_callback
        self.font_small = pygame.font.Font(None, 16)
        self.font_medium = pygame.font.Font(None, 20)
        self.font_large = pygame.font.Font(None, 24)
        self.error_message = ""
        self.error_timer = 0

    def draw(self, surface: pygame.Surface):
        surface.fill(COLOR_BG)

    def handle_event(self, event: pygame.event.Event) -> Optional[MenuState]:
        return None

    def update(self, dt: float):
        if self.error_timer > 0:
            self.error_timer -= dt
        else:
            self.error_message = ""

    def set_error(self, message: str):
        self.error_message = message
        self.error_timer = 3.0

    def draw_error(self, surface: pygame.Surface):
        if self.error_message:
            error_surface = self.font_small.render(self.error_message, True, (255, 100, 100))
            error_rect = error_surface.get_rect()
            error_rect.bottomleft = (10, HEIGHT - 10)
            pygame.draw.rect(surface, (40, 20, 20), error_rect.inflate(10, 10))
            pygame.draw.rect(surface, (255, 100, 100), error_rect.inflate(10, 10), 2)
            surface.blit(error_surface, error_rect)


class MainMenuScreen(MenuScreen):
    def __init__(self):
        super().__init__(MenuState.MAIN_MENU)
        self.play_button = create_button(WIDTH // 2 - 100, 200, 200, 50, "Play")
        self.build_button = create_button(WIDTH // 2 - 100, 270, 200, 50, "Build")
        self.exit_button = create_button(WIDTH // 2 - 100, 340, 200, 50, "Exit")
        self.buttons = [self.play_button, self.build_button, self.exit_button]

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        title = self.font_large.render("Dice Combat Dungeon", True, (255, 255, 255))
        title_rect = title.get_rect(center=(WIDTH // 2, 100))
        surface.blit(title, title_rect)

        for button in self.buttons:
            button.draw(surface, self.font_medium)

        self.draw_error(surface)

    def handle_event(self, event: pygame.event.Event) -> Optional[MenuState]:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.play_button.rect.collidepoint(event.pos):
                return MenuState.EXPLORING
            elif self.build_button.rect.collidepoint(event.pos):
                return MenuState.BUILD_MENU
            elif self.exit_button.rect.collidepoint(event.pos):
                return "EXIT"
        return None

    def update(self, dt: float):
        super().update(dt)
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            button.update(mouse_pos)


class BuildMenuScreen(MenuScreen):
    def __init__(self):
        super().__init__(MenuState.BUILD_MENU)
        self.status_button = create_button(WIDTH // 2 - 100, 200, 200, 50, "Build Status")
        self.skill_button = create_button(WIDTH // 2 - 100, 270, 200, 50, "Build Skill")
        self.creature_button = create_button(WIDTH // 2 - 100, 340, 200, 50, "Build Creature")
        self.back_button = create_button(WIDTH // 2 - 100, 410, 200, 50, "Back")
        self.buttons = [self.status_button, self.skill_button, self.creature_button, self.back_button]

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        title = self.font_large.render("Build Menu", True, (255, 255, 255))
        title_rect = title.get_rect(center=(WIDTH // 2, 100))
        surface.blit(title, title_rect)

        for button in self.buttons:
            button.draw(surface, self.font_medium)

        self.draw_error(surface)

    def handle_event(self, event: pygame.event.Event) -> Optional[MenuState]:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.status_button.rect.collidepoint(event.pos):
                return MenuState.STATUS_BUILDER
            elif self.skill_button.rect.collidepoint(event.pos):
                return MenuState.SKILL_BUILDER
            elif self.creature_button.rect.collidepoint(event.pos):
                return MenuState.CREATURE_BUILDER
            elif self.back_button.rect.collidepoint(event.pos):
                return MenuState.MAIN_MENU
        return None

    def update(self, dt: float):
        super().update(dt)
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            button.update(mouse_pos)


class StatusBuilderScreen(MenuScreen):
    def __init__(self):
        super().__init__(MenuState.STATUS_BUILDER)
        self.id_input = TextInput(pygame.Rect(100, 50, 300, 24), "Status ID:")
        self.name_input = TextInput(pygame.Rect(100, 90, 300, 24), "Status Name:")
        self.desc_input = TextInput(pygame.Rect(100, 130, 300, 80), "Description:")
        self.decays_checkbox = Checkbox(pygame.Rect(100, 220, 20, 20), "Decays", True)
        
        self.effects = []
        self.add_effect_button = create_button(100, 260, 200, 30, "Add Effect")
        self.remove_effect_button = create_button(320, 260, 200, 30, "Remove Last Effect")
        
        self.save_button = create_button(50, HEIGHT - 50, 150, 40, "Save")
        self.discard_button = create_button(WIDTH - 200, HEIGHT - 50, 150, 40, "Discard")
        
        self.effect_builder = None

    def draw(self, surface: pygame.Surface):
        if self.effect_builder:
            self.effect_builder.draw(surface)
            return
        
        super().draw(surface)
        draw_text(surface, "Create Status", (WIDTH // 2 - 50, 10), self.font_large)
        
        self.id_input.draw(surface, self.font_small)
        self.name_input.draw(surface, self.font_small)
        self.desc_input.draw(surface, self.font_small)
        self.decays_checkbox.draw(surface, self.font_small)
        
        self.add_effect_button.draw(surface, self.font_small)
        self.remove_effect_button.draw(surface, self.font_small)

        effect_y = 310
        draw_text(surface, "Effects:", (100, effect_y), self.font_medium)
        for i, effect in enumerate(self.effects):
            draw_text(surface, f"  {i+1}. {effect.describe()}", (110, effect_y + 30 + i * 25), self.font_small)

        self.save_button.draw(surface, self.font_medium)
        self.discard_button.draw(surface, self.font_medium)
        self.draw_error(surface)

    def handle_event(self, event: pygame.event.Event) -> Optional[MenuState]:
        if self.effect_builder:
            if not self.effect_builder.handle_event(event):
                self.effect_builder = None
            return None
        
        self.id_input.handle_event(event)
        self.name_input.handle_event(event)
        self.desc_input.handle_event(event)
        self.decays_checkbox.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.add_effect_button.rect.collidepoint(event.pos):
                self.effect_builder = EffectBuilderScreen(
                    on_complete=lambda e: self.effects.append(e),
                    on_cancel=None
                )
            elif self.remove_effect_button.rect.collidepoint(event.pos):
                if self.effects:
                    self.effects.pop()
            elif self.save_button.rect.collidepoint(event.pos):
                return self._save_status()
            elif self.discard_button.rect.collidepoint(event.pos):
                return MenuState.BUILD_MENU

        return None

    def _save_status(self) -> Optional[MenuState]:
        if not self.id_input.text or not self.name_input.text:
            self.set_error("ID and Name are required!")
            return None

        status = Status(
            self.id_input.text,
            self.name_input.text,
            self.desc_input.text,
            decays=self.decays_checkbox.checked,
            effects=self.effects
        )

        self._save_to_json(status)
        return MenuState.BUILD_MENU

    def _save_to_json(self, status: Status):
        file_path = Path.cwd() / "built_statuses.json"
        data = {"statuses": []}
        
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
            except (json.JSONDecodeError, IOError):
                data = {"statuses": []}
        
        status_dict = {
            "id": status.id,
            "name": status.name,
            "description": status.description,
            "decays": status.decays,
            "effects": [
                {
                    "trigger": effect.trigger,
                    "action": effect.action,
                    "condition": effect.condition
                }
                for effect in status.effects
            ]
        }
        
        data["statuses"] = [s for s in data["statuses"] if s["id"] != status.id]
        data["statuses"].append(status_dict)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def update(self, dt: float):
        super().update(dt)
        if self.effect_builder:
            self.effect_builder.update(dt)
        else:
            mouse_pos = pygame.mouse.get_pos()
            self.add_effect_button.update(mouse_pos)
            self.remove_effect_button.update(mouse_pos)
            self.save_button.update(mouse_pos)
            self.discard_button.update(mouse_pos)


class SkillBuilderScreen(MenuScreen):
    def __init__(self):
        super().__init__(MenuState.SKILL_BUILDER)
        self.id_input = TextInput(pygame.Rect(100, 50, 300, 24), "Skill ID:")
        self.name_input = TextInput(pygame.Rect(100, 90, 300, 24), "Skill Name:")
        self.desc_input = TextInput(pygame.Rect(100, 130, 300, 80), "Description:")
        self.cost_input = NumberInput(pygame.Rect(100, 220, 100, 24), "Cost:", 0, 0, 100)
        
        self.targeting_options = ["self", "enemy", "cone", "ally"]
        self.targeting_dropdown = ScrollableList(
            pygame.Rect(100, 260, 300, 100),
            self.targeting_options,
            on_select=self._on_targeting_select,
            searchable=False
        )
        self.targeting_type = "enemy"
        
        self.dice = []
        self.effects = []
        self.add_die_button = create_button(100, 380, 150, 30, "Add Die")
        self.add_effect_button = create_button(270, 380, 200, 30, "Add Skill Effect")
        self.remove_die_button = create_button(100, 420, 150, 30, "Remove Last Die")
        
        self.save_button = create_button(50, HEIGHT - 50, 150, 40, "Save")
        self.discard_button = create_button(WIDTH - 200, HEIGHT - 50, 150, 40, "Discard")
        
        self.die_builder = None
        self.effect_builder = None

    def _on_targeting_select(self, value: str):
        self.targeting_type = value

    def draw(self, surface: pygame.Surface):
        if self.die_builder:
            self.die_builder.draw(surface)
            return
        
        if self.effect_builder:
            self.effect_builder.draw(surface)
            return
        
        super().draw(surface)
        draw_text(surface, "Create Skill", (WIDTH // 2 - 50, 10), self.font_large)
        
        self.id_input.draw(surface, self.font_small)
        self.name_input.draw(surface, self.font_small)
        self.desc_input.draw(surface, self.font_small)
        self.cost_input.draw(surface, self.font_small)
        
        draw_text(surface, "Targeting Type:", (100, 245), self.font_small)
        self.targeting_dropdown.draw(surface, self.font_small)
        
        self.add_die_button.draw(surface, self.font_small)
        self.add_effect_button.draw(surface, self.font_small)
        self.remove_die_button.draw(surface, self.font_small)
        
        dice_y = 470
        draw_text(surface, "Dice:", (100, dice_y), self.font_medium)
        for i, die in enumerate(self.dice):
            draw_text(surface, f"  Die {i+1}: {die.type} [{die.min_roll}-{die.max_roll}] ({len(die.effects)} effects)", 
                     (110, dice_y + 30 + i * 25), self.font_small)
        
        effect_y = dice_y + len(self.dice) * 25 + 60
        draw_text(surface, "Effects:", (100, effect_y), self.font_medium)
        for i, effect in enumerate(self.effects):
            draw_text(surface, f"  {i+1}. {effect.describe()}", (110, effect_y + 30 + i * 25), self.font_small)
        
        self.save_button.draw(surface, self.font_medium)
        self.discard_button.draw(surface, self.font_medium)
        self.draw_error(surface)

    def handle_event(self, event: pygame.event.Event) -> Optional[MenuState]:
        if self.die_builder:
            if not self.die_builder.handle_event(event):
                self.die_builder = None
            return None
        
        if self.effect_builder:
            if not self.effect_builder.handle_event(event):
                self.effect_builder = None
            return None
        
        self.id_input.handle_event(event)
        self.name_input.handle_event(event)
        self.desc_input.handle_event(event)
        self.cost_input.handle_event(event)
        self.targeting_dropdown.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.add_die_button.rect.collidepoint(event.pos):
                self.die_builder = DieBuilderScreen(
                    on_complete=lambda d: self.dice.append(d),
                    on_cancel=None
                )
            elif self.add_effect_button.rect.collidepoint(event.pos):
                self.effect_builder = EffectBuilderScreen(
                    on_complete=lambda e: self.effects.append(e),
                    on_cancel=None
                )
            elif self.remove_die_button.rect.collidepoint(event.pos):
                if self.dice:
                    self.dice.pop()
            elif self.save_button.rect.collidepoint(event.pos):
                return self._save_skill()
            elif self.discard_button.rect.collidepoint(event.pos):
                return MenuState.BUILD_MENU

        return None

    def _save_skill(self) -> Optional[MenuState]:
        if not self.id_input.text or not self.name_input.text or not self.dice:
            self.set_error("ID, Name, and at least one Die are required!")
            return None

        skill = Skill(
            self.name_input.text,
            self.desc_input.text,
            self.cost_input.value,
            self.targeting_type,
            self.dice
        )
        skill.effects = self.effects

        self._save_to_json(self.id_input.text, skill)
        return MenuState.BUILD_MENU

    def _save_to_json(self, skill_id: str, skill: Skill):
        file_path = Path.cwd() / "built_skills.json"
        data = {"skills": []}
        
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
            except (json.JSONDecodeError, IOError):
                data = {"skills": []}
        
        skill_dict = {
            "id": skill_id,
            "name": skill.name,
            "description": skill.description,
            "cost": skill.cost,
            "targeting_type": skill.targeting_type,
            "dice": [
                {
                    "type": die.type,
                    "range": [die.min_roll, die.max_roll],
                    "effects": [
                        {
                            "trigger": effect.trigger,
                            "action": effect.action,
                            "condition": effect.condition
                        }
                        for effect in die.effects
                    ]
                }
                for die in skill.dice
            ],
            "effects": [
                {
                    "trigger": effect.trigger,
                    "action": effect.action,
                    "condition": effect.condition
                }
                for effect in skill.effects
            ]
        }
        
        data["skills"] = [s for s in data["skills"] if s["id"] != skill_id]
        data["skills"].append(skill_dict)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def update(self, dt: float):
        super().update(dt)
        if self.die_builder:
            self.die_builder.update(dt)
        elif self.effect_builder:
            self.effect_builder.update(dt)
        else:
            mouse_pos = pygame.mouse.get_pos()
            self.add_die_button.update(mouse_pos)
            self.add_effect_button.update(mouse_pos)
            self.remove_die_button.update(mouse_pos)
            self.save_button.update(mouse_pos)
            self.discard_button.update(mouse_pos)


class CreatureBuilderScreen(MenuScreen):
    def __init__(self):
        super().__init__(MenuState.CREATURE_BUILDER)
        self.id_input = TextInput(pygame.Rect(100, 50, 300, 24), "Creature ID:")
        self.name_input = TextInput(pygame.Rect(100, 90, 300, 24), "Creature Name:")
        self.desc_input = TextInput(pygame.Rect(100, 130, 300, 80), "Description:")
        self.hp_input = NumberInput(pygame.Rect(100, 220, 100, 24), "HP:", 10, 1, 1000)
        self.sr_input = NumberInput(pygame.Rect(220, 220, 100, 24), "SR:", 10, 0, 1000)
        self.max_points_input = NumberInput(pygame.Rect(100, 250, 100, 24), "Max Points:", -1, -1, 1000)
        
        self.deck = []
        self.statuses = []
        self.pending_statuses = []
        
        self.add_skill_button = create_button(100, 290, 150, 30, "Add Skill to Deck")
        self.remove_skill_button = create_button(270, 290, 150, 30, "Remove Last Skill")
        self.add_status_button = create_button(100, 330, 150, 30, "Add Status")
        self.remove_status_button = create_button(270, 330, 150, 30, "Remove Last Status")
        
        self.save_button = create_button(50, HEIGHT - 50, 150, 40, "Save")
        self.discard_button = create_button(WIDTH - 200, HEIGHT - 50, 150, 40, "Discard")
        
        self.skill_picker = None
        self.status_picker = None

    def draw(self, surface: pygame.Surface):
        if self.skill_picker:
            self.skill_picker.draw(surface)
            return
        
        if self.status_picker:
            self.status_picker.draw(surface)
            return
        
        super().draw(surface)
        draw_text(surface, "Create Creature", (WIDTH // 2 - 60, 10), self.font_large)
        
        self.id_input.draw(surface, self.font_small)
        self.name_input.draw(surface, self.font_small)
        self.desc_input.draw(surface, self.font_small)
        self.hp_input.draw(surface, self.font_small)
        self.sr_input.draw(surface, self.font_small)
        self.max_points_input.draw(surface, self.font_small)
        
        self.add_skill_button.draw(surface, self.font_small)
        self.remove_skill_button.draw(surface, self.font_small)
        self.add_status_button.draw(surface, self.font_small)
        self.remove_status_button.draw(surface, self.font_small)
        
        deck_y = 380
        draw_text(surface, f"Deck ({len(self.deck)} skills):", (100, deck_y), self.font_medium)
        for i, skill in enumerate(self.deck):
            draw_text(surface, f"  {i+1}. {skill.name} (Cost: {skill.cost})", (110, deck_y + 30 + i * 20), self.font_small)
        
        status_y = deck_y + len(self.deck) * 20 + 50
        draw_text(surface, f"Starting Statuses ({len(self.statuses)}):", (100, status_y), self.font_medium)
        for i, status_data in enumerate(self.statuses):
            status_name = status_data['status'].get('name', 'Unknown')
            draw_text(surface, f"  {i+1}. {status_name} (x{status_data['count']})", (110, status_y + 30 + i * 20), self.font_small)
        
        self.save_button.draw(surface, self.font_medium)
        self.discard_button.draw(surface, self.font_medium)
        self.draw_error(surface)

    def handle_event(self, event: pygame.event.Event) -> Optional[MenuState]:
        if self.skill_picker:
            if not self.skill_picker.handle_event(event):
                self.skill_picker = None
            return None
        
        if self.status_picker:
            if not self.status_picker.handle_event(event):
                self.status_picker = None
            return None
        
        self.id_input.handle_event(event)
        self.name_input.handle_event(event)
        self.desc_input.handle_event(event)
        self.hp_input.handle_event(event)
        self.sr_input.handle_event(event)
        self.max_points_input.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.add_skill_button.rect.collidepoint(event.pos):
                self.skill_picker = SkillPickerScreen(
                    on_select=self._add_skill,
                    on_cancel=None,
                    multi_select=False
                )
            elif self.remove_skill_button.rect.collidepoint(event.pos):
                if self.deck:
                    self.deck.pop()
            elif self.add_status_button.rect.collidepoint(event.pos):
                self.status_picker = StatusPickerScreen(
                    on_select=self._add_status,
                    on_cancel=None
                )
            elif self.remove_status_button.rect.collidepoint(event.pos):
                if self.statuses:
                    self.statuses.pop()
            elif self.save_button.rect.collidepoint(event.pos):
                return self._save_creature()
            elif self.discard_button.rect.collidepoint(event.pos):
                return MenuState.BUILD_MENU

        return None

    def _add_skill(self, skill_data: dict):
        from engine import Engine
        engine = Engine()
        try:
            skill = engine.load_skill(skill_data['id'])
            self.deck.append(skill)
        except:
            skill = Skill(skill_data['name'], skill_data.get('description', ''), 
                         skill_data.get('cost', 0), skill_data.get('targeting_type', 'enemy'), [])
            self.deck.append(skill)

    def _add_status(self, status_data: dict):
        self.statuses.append(status_data)

    def _save_creature(self) -> Optional[MenuState]:
        if not self.id_input.text or not self.name_input.text or not self.deck:
            self.set_error("ID, Name, and at least one Skill are required!")
            return None

        slots = []
        creature = Creature(
            self.name_input.text,
            self.desc_input.text,
            self.hp_input.value,
            self.sr_input.value,
            {},
            slots,
            self.deck,
            self.max_points_input.value
        )
        
        for status_data in self.statuses:
            creature.pending_statuses.append({
                'status': status_data['status']['id'],
                'potency': status_data['potency'],
                'count': status_data['count'],
                'delay': 0
            })

        self._save_to_json(self.id_input.text, creature)
        return MenuState.BUILD_MENU

    def _save_to_json(self, creature_id: str, creature: Creature):
        file_path = Path.cwd() / "built_creatures.json"
        data = {"enemies": []}
        
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
            except (json.JSONDecodeError, IOError):
                data = {"enemies": []}
        
        creature_dict = {
            "id": creature_id,
            "name": creature.name,
            "description": creature.description,
            "HP": creature.max_HP,
            "SR": creature.max_SR,
            "resist": creature.resist,
            "deck": [skill.id if hasattr(skill, 'id') else skill.name for skill in creature.deck],
            "max_points": creature.max_points,
            "pending_statuses": creature.pending_statuses
        }
        
        data["enemies"] = [c for c in data["enemies"] if c["id"] != creature_id]
        data["enemies"].append(creature_dict)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def update(self, dt: float):
        super().update(dt)
        if self.skill_picker:
            self.skill_picker.update(dt)
        elif self.status_picker:
            self.status_picker.update(dt)
        else:
            mouse_pos = pygame.mouse.get_pos()
            self.add_skill_button.update(mouse_pos)
            self.remove_skill_button.update(mouse_pos)
            self.add_status_button.update(mouse_pos)
            self.remove_status_button.update(mouse_pos)
            self.save_button.update(mouse_pos)
            self.discard_button.update(mouse_pos)
