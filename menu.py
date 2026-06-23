import pygame
from enum import Enum, auto
from typing import Callable, Any, Optional
from config import WIDTH, HEIGHT, COLOR_BG


class MenuState(Enum):
    MAIN_MENU = auto()
    BUILD_MENU = auto()
    STATUS_BUILDER = auto()
    SKILL_BUILDER = auto()
    CREATURE_BUILDER = auto()
    EFFECT_EDITOR = auto()
    DIE_EDITOR = auto()
    TRIGGER_SELECTOR = auto()
    ACTION_SELECTOR = auto()
    CONDITION_SELECTOR = auto()
    TARGET_SELECTOR = auto()
    STATUS_PICKER = auto()
    SKILL_PICKER = auto()
    EXPLORING = auto()


class Button:
    def __init__(self, rect: pygame.Rect, text: str, callback: Callable = None):
        self.rect = rect
        self.text = text
        self.callback = callback
        self.hovered = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, color=(255, 255, 255)):
        fill_color = (100, 100, 140) if self.hovered else (50, 50, 80)
        pygame.draw.rect(surface, fill_color, self.rect)
        pygame.draw.rect(surface, color, self.rect, 2)
        text_surface = font.render(self.text, True, color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def update(self, mouse_pos: tuple):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def click(self):
        if self.callback:
            self.callback()


class TextInput:
    def __init__(self, rect: pygame.Rect, label: str = "", default: str = ""):
        self.rect = rect
        self.label = label
        self.text = default
        self.active = False
        self.cursor_pos = len(self.text)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        if self.label:
            label_surface = font.render(self.label, True, (255, 255, 255))
            surface.blit(label_surface, (self.rect.x, self.rect.y - 20))
        
        bg_color = (80, 80, 80) if self.active else (50, 50, 50)
        pygame.draw.rect(surface, bg_color, self.rect)
        pygame.draw.rect(surface, (150, 150, 150) if self.active else (100, 100, 100), self.rect, 2)

        text_surface = font.render(self.text, True, (255, 255, 255))
        surface.blit(text_surface, (self.rect.x + 4, self.rect.y + 4))

        if self.active:
            cursor_x = self.rect.x + 4 + font.size(self.text[:self.cursor_pos])[0]
            pygame.draw.line(surface, (255, 255, 255), (cursor_x, self.rect.y + 4), (cursor_x, self.rect.y + self.rect.height - 4))

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                    self.cursor_pos -= 1
            elif event.key == pygame.K_DELETE:
                if self.cursor_pos < len(self.text):
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
            elif event.key == pygame.K_LEFT:
                self.cursor_pos = max(0, self.cursor_pos - 1)
            elif event.key == pygame.K_RIGHT:
                self.cursor_pos = min(len(self.text), self.cursor_pos + 1)
            elif event.key == pygame.K_HOME:
                self.cursor_pos = 0
            elif event.key == pygame.K_END:
                self.cursor_pos = len(self.text)
            elif event.unicode and event.unicode.isprintable():
                self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                self.cursor_pos += 1


class ScrollableList:
    def __init__(self, rect: pygame.Rect, items: list[str], on_select: Callable[[str], None] = None, searchable: bool = False):
        self.rect = rect
        self.items = items
        self.on_select = on_select
        self.searchable = searchable
        self.search_text = ""
        self.scroll_offset = 0
        self.selected_index = -1
        self.item_height = 24

        if searchable:
            self.search_input = TextInput(pygame.Rect(rect.x, rect.y - 30, rect.width, 24), "Search:")
        else:
            self.search_input = None

    def get_filtered_items(self) -> list[str]:
        if not self.search_text:
            return self.items
        return [item for item in self.items if self.search_text.lower() in item.lower()]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        if self.search_input:
            self.search_input.draw(surface, font)

        pygame.draw.rect(surface, (30, 30, 30), self.rect)
        pygame.draw.rect(surface, (150, 150, 150), self.rect, 2)

        filtered = self.get_filtered_items()
        visible_count = max(1, self.rect.height // self.item_height)
        
        if not filtered:
            self.scroll_offset = 0
            self.selected_index = -1
        elif self.scroll_offset >= len(filtered):
            self.scroll_offset = max(0, len(filtered) - visible_count)

        for i in range(visible_count):
            idx = i + self.scroll_offset
            if 0 <= idx < len(filtered):
                item = filtered[idx]
                item_rect = pygame.Rect(self.rect.x, self.rect.y + i * self.item_height, self.rect.width, self.item_height)
                
                if idx == self.selected_index:
                    pygame.draw.rect(surface, (80, 80, 120), item_rect)
                
                text_surface = font.render(item, True, (255, 255, 255))
                surface.blit(text_surface, (item_rect.x + 4, item_rect.y + 2))

    def handle_event(self, event: pygame.event.Event):
        if self.search_input:
            self.search_input.handle_event(event)
            old_search_text = self.search_text
            self.search_text = self.search_input.text
            
            if self.search_text != old_search_text:
                self.scroll_offset = 0
                self.selected_index = -1

        filtered = self.get_filtered_items()
        visible_count = self.rect.height // self.item_height

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                relative_y = event.pos[1] - self.rect.y
                item_index = relative_y // self.item_height + self.scroll_offset
                if 0 <= item_index < len(filtered):
                    self.selected_index = item_index
                    if self.on_select:
                        self.on_select(filtered[item_index])
            elif event.button == 4:
                self.scroll_offset = max(0, self.scroll_offset - 3)
            elif event.button == 5:
                self.scroll_offset = min(max(0, len(filtered) - visible_count), self.scroll_offset + 3)

    def update_items(self, items: list[str]):
        self.items = items
        self.scroll_offset = 0
        self.selected_index = -1


class Checkbox:
    def __init__(self, rect: pygame.Rect, label: str = "", checked: bool = False):
        self.rect = rect
        self.label = label
        self.checked = checked
        self.checkbox_rect = pygame.Rect(rect.x, rect.y, 20, 20)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        pygame.draw.rect(surface, (50, 50, 80), self.checkbox_rect)
        pygame.draw.rect(surface, (150, 150, 150), self.checkbox_rect, 2)
        
        if self.checked:
            pygame.draw.line(surface, (100, 255, 100), (self.checkbox_rect.x + 4, self.checkbox_rect.y + 10),
                           (self.checkbox_rect.x + 8, self.checkbox_rect.y + 14), 2)
            pygame.draw.line(surface, (100, 255, 100), (self.checkbox_rect.x + 8, self.checkbox_rect.y + 14),
                           (self.checkbox_rect.x + 16, self.checkbox_rect.y + 4), 2)
        
        if self.label:
            label_surface = font.render(self.label, True, (255, 255, 255))
            surface.blit(label_surface, (self.checkbox_rect.right + 8, self.checkbox_rect.y + 2))

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.checkbox_rect.collidepoint(event.pos):
                self.checked = not self.checked

    def update(self, mouse_pos: tuple):
        pass


class NumberInput:
    def __init__(self, rect: pygame.Rect, label: str = "", default: int = 0, min_val: int = 0, max_val: int = 1000):
        self.rect = rect
        self.label = label
        self.value = default
        self.min_val = min_val
        self.max_val = max_val
        self.text_input = TextInput(rect, "", str(default))

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        if self.label:
            label_surface = font.render(self.label, True, (255, 255, 255))
            surface.blit(label_surface, (self.rect.x, self.rect.y - 20))
        
        self.text_input.draw(surface, font)

    def handle_event(self, event: pygame.event.Event):
        self.text_input.handle_event(event)
        try:
            val = int(self.text_input.text) if self.text_input.text else 0
            self.value = max(self.min_val, min(self.max_val, val))
        except ValueError:
            pass

    @property
    def text(self):
        return str(self.value)


def draw_text(surface, text, position, font, color=(255, 255, 255)):
    if not text:
        return
    lines = text.split('\n')
    for index, line in enumerate(lines):
        surface.blit(font.render(line, True, color), (position[0], position[1] + index * (font.get_height() + 2)))


def create_button(x, y, width, height, text, callback=None):
    return Button(pygame.Rect(x, y, width, height), text, callback)


def create_text_input(x, y, width, height, label="", default=""):
    return TextInput(pygame.Rect(x, y, width, height), label, default)
