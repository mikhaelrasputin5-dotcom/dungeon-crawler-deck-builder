import pygame
from typing import Optional
from enum import Enum, auto

from menu import MenuState
from menu_screens import (
    MainMenuScreen, BuildMenuScreen, StatusBuilderScreen,
    SkillBuilderScreen, CreatureBuilderScreen
)


class MenuManager:
    def __init__(self):
        self.current_screen = MainMenuScreen()
        self.previous_screens = []
        self.running = True
        self.should_start_game = False
        self.should_exit = False

    def handle_event(self, event: pygame.event.Event):
        result = self.current_screen.handle_event(event)
        
        if result is None:
            return
        
        if result == "EXIT":
            self.should_exit = True
            self.running = False
        elif result == MenuState.EXPLORING:
            self.should_start_game = True
            self.running = False
        elif isinstance(result, MenuState):
            self._transition_to(result)

    def _transition_to(self, state: MenuState):
        new_screen = None
        
        match state:
            case MenuState.MAIN_MENU:
                new_screen = MainMenuScreen()
            case MenuState.BUILD_MENU:
                new_screen = BuildMenuScreen()
            case MenuState.STATUS_BUILDER:
                new_screen = StatusBuilderScreen()
            case MenuState.SKILL_BUILDER:
                new_screen = SkillBuilderScreen()
            case MenuState.CREATURE_BUILDER:
                new_screen = CreatureBuilderScreen()
            case _:
                return
        
        if new_screen:
            self.current_screen = new_screen

    def update(self, dt: float):
        self.current_screen.update(dt)

    def draw(self, surface: pygame.Surface):
        self.current_screen.draw(surface)

    def is_running(self) -> bool:
        return self.running

    def should_play(self) -> bool:
        return self.should_start_game

    def should_exit_game(self) -> bool:
        return self.should_exit
