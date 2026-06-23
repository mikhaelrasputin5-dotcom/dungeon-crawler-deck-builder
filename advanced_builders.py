import pygame
import json
from pathlib import Path
from typing import Optional
from enum import Enum, auto

from menu import (
    MenuState, Button, TextInput, ScrollableList, Checkbox, NumberInput,
    draw_text, create_button
)
from config import WIDTH, HEIGHT, COLOR_BG
from effect import Effect
from die import Die


class EffectBuilderScreen:
    def __init__(self, on_complete: callable = None, on_cancel: callable = None):
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.font_small = pygame.font.Font(None, 16)
        self.font_medium = pygame.font.Font(None, 20)
        self.font_large = pygame.font.Font(None, 24)
        
        self.error_message = ""
        self.error_timer = 0
        self.triggers = [
            "on_play", "on_clash", "on_clash_start", "on_win", "on_lose",
            "on_die_roll", "on_die_max", "on_unopposed_attack", "on_evade_success",
            "on_evade_fail", "on_turn_start", "on_turn_end", "on_stagger",
            "on_take_damage", "on_status_applied"
        ]
        self.trigger_list = ScrollableList(
            pygame.Rect(20, 50, 300, 150),
            self.triggers,
            searchable=True
        )
        self.selected_trigger = None
        
        self.action_types = [
            "modify_max_roll", "modify_min_roll", "inflict_status",
            "grant_next_turn_status", "double_damage", "heal",
            "damage_by_potency", "restore_points", "restore_points_to_max",
            "draw_skills", "draw_if_empty_hand", "refresh_if_deck_empty",
            "refresh", "gain_shield"
        ]
        self.action_list = ScrollableList(
            pygame.Rect(350, 50, 300, 150),
            self.action_types,
            searchable=True
        )
        self.selected_action = None
        
        self.action_params = {}
        self.setup_action_inputs()
        self.condition_types = [
            "None",
            "status_count",
            "consecutive_wins",
            "opponent_skill_type"
        ]
        self.condition_list = ScrollableList(
            pygame.Rect(20, 220, 300, 100),
            self.condition_types,
            searchable=False
        )
        self.selected_condition = None
        self.condition_params = {}
        
        self.targets = ["self", "target", "defender", "ally", "enemy"]
        self.target_dropdown = ScrollableList(
            pygame.Rect(350, 220, 300, 100),
            self.targets,
            searchable=False
        )
        self.selected_target = "target"
        
        self.save_button = create_button(50, HEIGHT - 50, 150, 40, "Add Effect")
        self.cancel_button = create_button(WIDTH - 200, HEIGHT - 50, 150, 40, "Cancel")

    def setup_action_inputs(self):
        self.action_params = {}
        
        if self.selected_action == "modify_max_roll" or self.selected_action == "modify_min_roll":
            self.action_params["value"] = NumberInput(
                pygame.Rect(350, 170, 100, 24), "Value:", 1, -100, 100
            )
        elif self.selected_action == "inflict_status":
            self.action_params["status"] = TextInput(
                pygame.Rect(350, 170, 200, 24), "Status ID:"
            )
            self.action_params["potency"] = NumberInput(
                pygame.Rect(560, 170, 80, 24), "Potency:", 1, 0, 100
            )
            self.action_params["count"] = NumberInput(
                pygame.Rect(350, 200, 80, 24), "Count:", 1, 0, 100
            )
        elif self.selected_action == "grant_next_turn_status":
            self.action_params["status"] = TextInput(
                pygame.Rect(350, 170, 200, 24), "Status ID:"
            )
            self.action_params["potency"] = NumberInput(
                pygame.Rect(560, 170, 80, 24), "Potency:", 1, 0, 100
            )
            self.action_params["count"] = NumberInput(
                pygame.Rect(350, 200, 80, 24), "Count:", 1, 0, 100
            )
        elif self.selected_action == "double_damage":
            self.action_params["multiplier"] = NumberInput(
                pygame.Rect(350, 170, 100, 24), "Multiplier:", 2, 1, 10
            )
        elif self.selected_action == "heal":
            self.action_params["amount"] = NumberInput(
                pygame.Rect(350, 170, 100, 24), "Amount:", 10, 0, 1000
            )
        elif self.selected_action == "damage_by_potency":
            self.action_params["status"] = TextInput(
                pygame.Rect(350, 170, 200, 24), "Status ID:"
            )
            self.action_params["multiplier"] = NumberInput(
                pygame.Rect(560, 170, 80, 24), "Multiplier:", 1, 0, 10
            )
        elif self.selected_action == "restore_points":
            self.action_params["points"] = NumberInput(
                pygame.Rect(350, 170, 100, 24), "Points:", 1, 0, 100
            )
        elif self.selected_action == "draw_skills":
            self.action_params["count"] = NumberInput(
                pygame.Rect(350, 170, 100, 24), "Count:", 1, 1, 20
            )
        elif self.selected_action == "draw_if_empty_hand":
            self.action_params["count"] = NumberInput(
                pygame.Rect(350, 170, 100, 24), "Count:", 1, 1, 20
            )
        elif self.selected_action == "gain_shield":
            self.action_params["amount"] = NumberInput(
                pygame.Rect(350, 170, 100, 24), "Amount:", 5, 0, 1000
            )

    def setup_condition_inputs(self):
        self.condition_params = {}
        
        if self.selected_condition == "status_count":
            self.condition_params["status"] = TextInput(
                pygame.Rect(20, 380, 200, 24), "Status ID:"
            )
            self.condition_params["value"] = NumberInput(
                pygame.Rect(230, 380, 80, 24), "Count:", 1, 0, 100
            )
        elif self.selected_condition == "consecutive_wins":
            self.condition_params["value"] = NumberInput(
                pygame.Rect(20, 380, 100, 24), "Wins:", 1, 1, 100
            )
        elif self.selected_condition == "opponent_skill_type":
            self.condition_params["skill_type"] = TextInput(
                pygame.Rect(20, 380, 200, 24), "Skill Type:"
            )

    def draw(self, surface: pygame.Surface):
        surface.fill(COLOR_BG)
        
        draw_text(surface, "Effect Builder", (20, 10), self.font_large)
        
        draw_text(surface, "Trigger:", (20, 30), self.font_medium)
        self.trigger_list.draw(surface, self.font_small)
        if self.selected_trigger:
            draw_text(surface, f"Selected: {self.selected_trigger}", (20, 210), self.font_small, (100, 255, 100))
        
        draw_text(surface, "Action:", (350, 30), self.font_medium)
        self.action_list.draw(surface, self.font_small)
        if self.selected_action:
            draw_text(surface, f"Selected: {self.selected_action}", (350, 210), self.font_small, (100, 255, 100))
        
        draw_text(surface, "Target:", (350, 200), self.font_medium)
        self.target_dropdown.draw(surface, self.font_small)
        
        param_y = 170
        for key, param in self.action_params.items():
            param.draw(surface, self.font_small)
            param_y += 35
        
        draw_text(surface, "Condition (optional):", (20, 330), self.font_medium)
        self.condition_list.draw(surface, self.font_small)
        if self.selected_condition and self.selected_condition != "None":
            draw_text(surface, f"Selected: {self.selected_condition}", (20, 440), self.font_small, (100, 255, 100))
        
        for key, param in self.condition_params.items():
            param.draw(surface, self.font_small)
        
        self.save_button.draw(surface, self.font_medium)
        self.cancel_button.draw(surface, self.font_medium)
        self.draw_error(surface)

    def draw_error(self, surface: pygame.Surface):
        if self.error_message:
            error_surface = self.font_small.render(self.error_message, True, (255, 100, 100))
            error_rect = error_surface.get_rect()
            error_rect.bottomleft = (10, HEIGHT - 10)
            pygame.draw.rect(surface, (40, 20, 20), error_rect.inflate(10, 10))
            pygame.draw.rect(surface, (255, 100, 100), error_rect.inflate(10, 10), 2)
            surface.blit(error_surface, error_rect)

    def set_error(self, message: str):
        self.error_message = message
        self.error_timer = 3.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        self.trigger_list.handle_event(event)
        trigger_items = self.trigger_list.get_filtered_items()
        if 0 <= self.trigger_list.selected_index < len(trigger_items):
            self.selected_trigger = trigger_items[self.trigger_list.selected_index]
        
        self.action_list.handle_event(event)
        action_items = self.action_list.get_filtered_items()
        if 0 <= self.action_list.selected_index < len(action_items):
            prev_action = self.selected_action
            self.selected_action = action_items[self.action_list.selected_index]
            if prev_action != self.selected_action:
                self.setup_action_inputs()
        
        self.target_dropdown.handle_event(event)
        target_items = self.target_dropdown.get_filtered_items()
        if 0 <= self.target_dropdown.selected_index < len(target_items):
            self.selected_target = target_items[self.target_dropdown.selected_index]
        
        self.condition_list.handle_event(event)
        condition_items = self.condition_list.get_filtered_items()
        if 0 <= self.condition_list.selected_index < len(condition_items):
            prev_condition = self.selected_condition
            self.selected_condition = condition_items[self.condition_list.selected_index]
            if prev_condition != self.selected_condition:
                self.setup_condition_inputs()
        
        # Handle parameter inputs
        for param in self.action_params.values():
            param.handle_event(event)
        
        # Handle condition parameter inputs
        for param in self.condition_params.values():
            param.handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.save_button.rect.collidepoint(event.pos):
                return self._save_effect()
            elif self.cancel_button.rect.collidepoint(event.pos):
                if self.on_cancel:
                    self.on_cancel()
                return False
        
        return True

    def _save_effect(self) -> bool:
        if not self.selected_trigger or not self.selected_action:
            self.set_error("Trigger and Action are required!")
            return True
        
        action = {
            "type": self.selected_action,
            "target": self.selected_target
        }
        
        for key, param in self.action_params.items():
            if isinstance(param, NumberInput):
                action[key] = param.value
            elif isinstance(param, TextInput):
                action[key] = param.text
        
        condition = None
        if self.selected_condition and self.selected_condition != "None":
            condition = {"type": self.selected_condition}
            for key, param in self.condition_params.items():
                if isinstance(param, NumberInput):
                    condition[key] = param.value
                elif isinstance(param, TextInput):
                    condition[key] = param.text
        
        effect = Effect(self.selected_trigger, action, condition)
        if self.on_complete:
            self.on_complete(effect)
        
        return False

    def update(self, dt: float):
        if self.error_timer > 0:
            self.error_timer -= dt
        else:
            self.error_message = ""
        
        mouse_pos = pygame.mouse.get_pos()
        self.save_button.update(mouse_pos)
        self.cancel_button.update(mouse_pos)


class DieBuilderScreen:
    def __init__(self, die=None, on_complete: callable = None, on_cancel: callable = None):
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.font_small = pygame.font.Font(None, 16)
        self.font_medium = pygame.font.Font(None, 20)
        self.font_large = pygame.font.Font(None, 24)
        
        self.error_message = ""
        self.error_timer = 0
        
        self.die_types = ["attack", "evade", "special"]
        self.type_dropdown = ScrollableList(
            pygame.Rect(100, 100, 300, 100),
            self.die_types,
            searchable=False
        )
        self.selected_type = "attack"
        
        self.min_roll_input = NumberInput(
            pygame.Rect(100, 220, 100, 24), "Min Roll:", 1, 1, 100
        )
        self.max_roll_input = NumberInput(
            pygame.Rect(220, 220, 100, 24), "Max Roll:", 6, 1, 100
        )
        
        self.effects = []
        self.add_effect_button = create_button(100, 260, 200, 30, "Add Effect")
        self.remove_effect_button = create_button(320, 260, 200, 30, "Remove Last")
        
        self.effect_builder = None
        
        self.save_button = create_button(50, HEIGHT - 50, 150, 40, "Save Die")
        self.cancel_button = create_button(WIDTH - 200, HEIGHT - 50, 150, 40, "Cancel")

    def draw(self, surface: pygame.Surface):
        surface.fill(COLOR_BG)
        
        if self.effect_builder:
            self.effect_builder.draw(surface)
            return
        
        draw_text(surface, "Die Builder", (20, 10), self.font_large)
        
        draw_text(surface, "Die Type:", (100, 80), self.font_medium)
        self.type_dropdown.draw(surface, self.font_small)
        
        self.min_roll_input.draw(surface, self.font_small)
        self.max_roll_input.draw(surface, self.font_small)
        
        self.add_effect_button.draw(surface, self.font_small)
        self.remove_effect_button.draw(surface, self.font_small)
        
        effect_y = 310
        draw_text(surface, "Effects:", (100, effect_y), self.font_medium)
        for i, effect in enumerate(self.effects):
            draw_text(surface, f"  {i+1}. {effect.describe()}", (110, effect_y + 30 + i * 25), self.font_small)
        
        self.save_button.draw(surface, self.font_medium)
        self.cancel_button.draw(surface, self.font_medium)
        self.draw_error(surface)

    def draw_error(self, surface: pygame.Surface):
        if self.error_message:
            error_surface = self.font_small.render(self.error_message, True, (255, 100, 100))
            error_rect = error_surface.get_rect()
            error_rect.bottomleft = (10, HEIGHT - 10)
            pygame.draw.rect(surface, (40, 20, 20), error_rect.inflate(10, 10))
            pygame.draw.rect(surface, (255, 100, 100), error_rect.inflate(10, 10), 2)
            surface.blit(error_surface, error_rect)

    def set_error(self, message: str):
        self.error_message = message
        self.error_timer = 3.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.effect_builder:
            if not self.effect_builder.handle_event(event):
                self.effect_builder = None
            return True
        
        self.type_dropdown.handle_event(event)
        if self.type_dropdown.selected_index >= 0:
            self.selected_type = self.type_dropdown.get_filtered_items()[self.type_dropdown.selected_index]
        
        self.min_roll_input.handle_event(event)
        self.max_roll_input.handle_event(event)
        
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
                if self.on_complete:
                    from die import Die
                    die = Die([self.min_roll_input.value, self.max_roll_input.value], self.selected_type, self.effects)
                    self.on_complete(die)
                return False
            elif self.cancel_button.rect.collidepoint(event.pos):
                if self.on_cancel:
                    self.on_cancel()
                return False
        
        return True

    def update(self, dt: float):
        if self.effect_builder:
            self.effect_builder.update(dt)
        
        if self.error_timer > 0:
            self.error_timer -= dt
        else:
            self.error_message = ""
        
        mouse_pos = pygame.mouse.get_pos()
        self.save_button.update(mouse_pos)
        self.cancel_button.update(mouse_pos)
