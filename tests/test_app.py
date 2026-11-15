"""Інтеграційні перевірки справжніх подій і поверхонь Pygame без монітора."""

import os
from pathlib import Path
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pygame

from dungeon_escape.app import Application
from dungeon_escape.model import State
from dungeon_escape.levels import LEVELS
from test_model import winning_actions


def press(app: Application, key: int) -> None:
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))


class PygameTests(unittest.TestCase):
    def tearDown(self):
        pygame.quit()

    def test_window_events_movement_restart_and_quit(self):
        app = Application("01")
        app.draw()
        press(app, pygame.K_RETURN)
        self.assertEqual(app.game.state, State.PLAYING)
        press(app, pygame.K_d)
        self.assertEqual(app.game.player, (2, 1))
        press(app, pygame.K_LEFT)
        self.assertEqual(app.game.player, (1, 1))
        press(app, pygame.K_DOWN)
        self.assertEqual(app.game.player, (1, 2))
        press(app, pygame.K_r)
        self.assertEqual(app.game.player, (1, 1))
        press(app, pygame.K_ESCAPE)
        press(app, pygame.K_r)
        self.assertEqual(app.game.state, State.EXIT)

    def test_all_levels_can_win_through_input_and_draw_terminal_screens(self):
        keys = {(0, -1): pygame.K_UP, (0, 1): pygame.K_DOWN, (-1, 0): pygame.K_LEFT, (1, 0): pygame.K_RIGHT}
        for number in LEVELS:
            with self.subTest(prototype=number):
                app = Application(number)
                app.draw()
                press(app, pygame.K_RETURN)
                for action in winning_actions(app.game.level):
                    if action is not None:
                        press(app, keys[action])
                    app.game.update(app.game.level.enemy_interval)
                    app.draw()
                self.assertEqual(app.game.state, State.WON)
                press(app, pygame.K_r)
                self.assertEqual(app.game.state, State.PLAYING)
                if app.game.enemy is not None:
                    # Імітуємо очікування на наступній клітинці патруля.
                    app.game.player = app.game.level.enemy_route[1]
                    app.game.update(app.game.level.enemy_interval)
                    self.assertEqual(app.game.state, State.LOST)
                    app.draw()
                    press(app, pygame.K_r)
                    self.assertEqual(app.game.state, State.PLAYING)
                app.handle_event(pygame.event.Event(pygame.QUIT))
                self.assertEqual(app.game.state, State.EXIT)

    def test_menu_selection_and_return(self):
        app = Application("01")
        press(app, pygame.K_UP)
        self.assertEqual(app.selected, len(LEVELS) - 1)
        press(app, pygame.K_DOWN)
        self.assertEqual(app.selected, 0)
        press(app, pygame.K_DOWN)
        press(app, pygame.K_RETURN)
        self.assertIs(app.game.level, LEVELS["02"])
        self.assertEqual(app.game.state, State.PLAYING)
        press(app, pygame.K_m)
        self.assertEqual(app.game.state, State.MENU)
        before = app.game.enemy
        app.game.update(10)
        self.assertEqual(app.game.enemy, before)
        app.draw()

    def test_mouse_starts_selected_level(self):
        app = Application("01")
        app.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=app.level_buttons()[4].center))
        self.assertIs(app.game.level, LEVELS["05"])
        self.assertEqual(app.game.state, State.PLAYING)
        self.assertFalse(app.game.has_key)
        app.draw()

    def test_next_level_and_end_of_last_level(self):
        app = Application("03")
        app.game.reset(State.WON)
        press(app, pygame.K_RETURN)
        self.assertIs(app.game.level, LEVELS["04"])
        self.assertEqual(app.game.state, State.PLAYING)
        self.assertFalse(app.game.has_key)
        app.load_level(len(LEVELS) - 1)
        app.game.reset(State.WON)
        press(app, pygame.K_RETURN)
        self.assertEqual(app.game.state, State.MENU)
        self.assertEqual(app.selected, 0)

    def test_ukrainian_alphabet_has_glyphs(self):
        app = Application("03")
        alphabet = "АаБбВвГгҐґДдЕеЄєЖжЗзИиІіЇїЙйКкЛлМмНнОоПпРрСсТтУуФфХхЦцЧчШшЩщЬьЮюЯя"
        self.assertTrue(all(metric is not None for metric in app.font.metrics(alphabet)))


if __name__ == "__main__":
    unittest.main()
