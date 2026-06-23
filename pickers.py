import pygame
import json
from pathlib import Path
from typing import Optional, Callable

from menu import ScrollableList, TextInput, Checkbox, NumberInput, Button, draw_text
from config import WIDTH, HEIGHT, COLOR_BG


class SkillPickerScreen:
    def __init__(self, on_select: Callable = None, on_cancel: Callable = None, multi_select: bool = False):
        self.on_select = on_select
        self.on_cancel = on_cancel
        self.multi_select = multi_select
        self.font_small = pygame.font.Font(None, 16)
        self.font_medium = pygame.font.Font(None, 20)
        self.font_large = pygame.font.Font(None, 24)
        
        self.error_message = ""
        self.error_timer = 0
        
        self.skills = self._load_skills()
        self.skill_list = ScrollableList(
            pygame.Rect(50, 80, 400, HEIGHT - 180),
            [skill["name"] for skill in self.skills],
            searchable=True
        )
        
        if multi_select:
            self.selected_skills = []
            self.skill_checkboxes = [Checkbox(pygame.Rect(420, 80 + i*25, 200, 20), skill["name"]) 
                                     for i, skill in enumerate(self.skills)]
        
        self.confirm_button = Button(pygame.Rect(50, HEIGHT - 50, 150, 40), "Confirm", None)
        self.cancel_button = Button(pygame.Rect(WIDTH - 200, HEIGHT - 50, 150, 40), "Cancel", None)

    def _load_skills(self) -> list[dict]:
        file_path = Path.cwd() / "built_skills.json"
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    return []
                data = json.loads(content)
                return data.get("skills", [])
        except Exception as e:
            self.set_error(f"Error loading skills: {str(e)}")
            return []

    def draw(self, surface: pygame.Surface):
        surface.fill(COLOR_BG)
        
        title = "Select Skill" if not self.multi_select else "Select Skills"
        draw_text(surface, title, (50, 30), self.font_large)
        
        self.skill_list.draw(surface, self.font_small)
        
        if self.multi_select and self.skills:
            selected_count = len(self.selected_skills)
            draw_text(surface, f"Selected: {selected_count}", (420, 50), self.font_small)
        
        self.confirm_button.draw(surface, self.font_medium)
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
        self.skill_list.handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.confirm_button.rect.collidepoint(event.pos):
                if self.multi_select:
                    if not self.selected_skills:
                        self.set_error("Select at least one skill!")
                        return True
                    if self.on_select:
                        self.on_select(self.selected_skills)
                else:
                    if self.skill_list.selected_index >= 0:
                        selected_skill = self.skills[self.skill_list.selected_index]
                        if self.on_select:
                            self.on_select(selected_skill)
                    else:
                        self.set_error("Select a skill first!")
                        return True
                return False
            elif self.cancel_button.rect.collidepoint(event.pos):
                if self.on_cancel:
                    self.on_cancel()
                return False
        
        return True

    def update(self, dt: float):
        if self.error_timer > 0:
            self.error_timer -= dt
        else:
            self.error_message = ""
        
        mouse_pos = pygame.mouse.get_pos()
        self.confirm_button.update(mouse_pos)
        self.cancel_button.update(mouse_pos)


class StatusPickerScreen:
    def __init__(self, on_select: Callable = None, on_cancel: Callable = None):
        self.on_select = on_select
        self.on_cancel = on_cancel
        self.font_small = pygame.font.Font(None, 16)
        self.font_medium = pygame.font.Font(None, 20)
        self.font_large = pygame.font.Font(None, 24)
        
        self.error_message = ""
        self.error_timer = 0
        
        self.statuses = self._load_statuses()
        self.status_list = ScrollableList(
            pygame.Rect(50, 80, 400, HEIGHT - 180),
            [status["name"] for status in self.statuses],
            searchable=True
        )
        
        self.potency_input = NumberInput(
            pygame.Rect(480, 100, 100, 24), "Potency:", 1, 0, 100
        )
        self.count_input = NumberInput(
            pygame.Rect(480, 140, 100, 24), "Stacks:", 1, 0, 100
        )
        
        self.confirm_button = Button(pygame.Rect(50, HEIGHT - 50, 150, 40), "Add Status", None)
        self.cancel_button = Button(pygame.Rect(WIDTH - 200, HEIGHT - 50, 150, 40), "Cancel", None)

    def _load_statuses(self) -> list[dict]:
        file_path = Path.cwd() / "built_statuses.json"
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    return []
                data = json.loads(content)
                return data.get("statuses", [])
        except Exception as e:
            self.set_error(f"Error loading statuses: {str(e)}")
            return []

    def draw(self, surface: pygame.Surface):
        surface.fill(COLOR_BG)
        
        draw_text(surface, "Select Status", (50, 30), self.font_large)
        
        self.status_list.draw(surface, self.font_small)
        
        if self.status_list.selected_index >= 0:
            selected = self.statuses[self.status_list.selected_index]
            draw_text(surface, f"Name: {selected['name']}", (480, 60), self.font_small)
            draw_text(surface, f"Desc: {selected.get('description', '')[:50]}", (480, 80), self.font_small)
            self.potency_input.draw(surface, self.font_small)
            self.count_input.draw(surface, self.font_small)
        
        self.confirm_button.draw(surface, self.font_medium)
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
        self.status_list.handle_event(event)
        self.potency_input.handle_event(event)
        self.count_input.handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.confirm_button.rect.collidepoint(event.pos):
                if self.status_list.selected_index >= 0:
                    selected_status = self.statuses[self.status_list.selected_index]
                    if self.on_select:
                        self.on_select({
                            "status": selected_status,
                            "potency": self.potency_input.value,
                            "count": self.count_input.value
                        })
                    return False
                else:
                    self.set_error("Select a status first!")
                    return True
            elif self.cancel_button.rect.collidepoint(event.pos):
                if self.on_cancel:
                    self.on_cancel()
                return False
        
        return True

    def update(self, dt: float):
        if self.error_timer > 0:
            self.error_timer -= dt
        else:
            self.error_message = ""
        
        mouse_pos = pygame.mouse.get_pos()
        self.confirm_button.update(mouse_pos)
        self.cancel_button.update(mouse_pos)
