"""Інтеграційні перевірки меню й керування двома гравцями."""
from collections import defaultdict
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import pygame
from dungeon_escape.app import Application
from dungeon_escape.model import State
from test_campaign import ROOM, finish_player
from playthrough import play_stage
from dungeon_escape.campaign import Session


def press(app, key):
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))


class PygameTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / 'progress.json'
        self.app = Application(progress_path=self.path)

    def tearDown(self):
        pygame.quit()
        self.temp.cleanup()

    def click(self, action):
        self.app.draw()
        rect = next(rect for rect, name in self.app.buttons if name == action)
        self.app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))

    def test_home_buttons_grid_and_mouse_start(self):
        self.click('coop')
        self.app.draw()
        numbers = [rect for rect, action in self.app.buttons if type(action) is int]
        self.assertEqual(len(numbers), 9)
        self.assertTrue(all(r.width == r.height and r.width >= 100 for r in numbers))
        self.assertEqual(len({r.centerx for r in numbers}), 3)
        self.assertEqual(len({r.centery for r in numbers}), 3)
        self.click(8)
        self.assertEqual(self.app.page, 'levels')
        self.assertTrue(self.app.notice)
        self.click(0)
        self.assertEqual(len(self.app.game.players), 2)
        self.assertEqual(self.app.game.stage.number, 1)

    def test_keyboard_navigation_and_back(self):
        press(self.app, pygame.K_RETURN)
        self.assertEqual(self.app.page, 'levels')
        press(self.app, pygame.K_DOWN)
        press(self.app, pygame.K_RIGHT)
        self.assertEqual(self.app.selected, 4)
        press(self.app, pygame.K_RETURN)
        self.assertEqual(self.app.page, 'levels')
        self.app.selected = 0
        press(self.app, pygame.K_RETURN)
        self.assertEqual(self.app.page, 'play')
        press(self.app, pygame.K_ESCAPE)
        self.assertEqual(self.app.page, 'levels')
        press(self.app, pygame.K_ESCAPE)
        self.assertEqual(self.app.page, 'home')

    def test_coop_controls_are_independent_and_can_be_held_together(self):
        self.app.mode = 'coop'
        self.app.load_level(0)
        self.app.game = Session(ROOM)
        press(self.app, pygame.K_RIGHT)
        self.assertEqual(self.app.game.players, [(2, 1), (1, 3)])
        press(self.app, pygame.K_d)
        self.assertEqual(self.app.game.players, [(2, 1), (2, 3)])
        held = defaultdict(bool, {pygame.K_RIGHT: True, pygame.K_d: True})
        with patch('pygame.key.get_pressed', return_value=held):
            self.app.update(0.2)
        self.assertEqual(self.app.game.players, [(3, 1), (3, 3)])

    def test_pause_blocks_world_and_input_then_resume(self):
        self.app.load_level(0)
        before = list(self.app.game.players)
        press(self.app, pygame.K_p)
        press(self.app, pygame.K_RIGHT)
        self.app.update(1)
        self.assertEqual(self.app.game.elapsed, 0)
        self.assertEqual(self.app.game.players, before)
        self.click('resume')
        self.assertFalse(self.app.paused)
        self.app.update(0.1)
        self.assertGreater(self.app.game.elapsed, 0)

    def test_progress_is_separate_persistent_and_handles_bad_file(self):
        self.app.load_level(0)
        play_stage(self.app.game)
        self.app.record_win()
        self.app.record_win()
        other = Application(progress_path=self.path)
        self.assertEqual(other.completed, {'solo': [1], 'coop': []})
        self.path.write_text('broken', encoding='utf-8')
        other = Application(progress_path=self.path)
        self.assertEqual(other.completed, {'solo': [], 'coop': []})

    def test_next_level_final_return_and_exit_button(self):
        self.app.load_level(0)
        self.app.game.state = State.WON
        press(self.app, pygame.K_RETURN)
        self.assertEqual(self.app.selected, 1)
        self.assertFalse(any(self.app.game.exit_keys))
        self.app.completed[self.app.mode] = list(range(1, 9))
        self.app.load_level(8)
        self.app.game.state = State.WON
        press(self.app, pygame.K_RETURN)
        self.assertEqual(self.app.page, 'levels')
        self.click('quit')
        press(self.app, pygame.K_r)
        self.assertEqual(self.app.game.state, State.EXIT)

    def test_all_eighteen_maps_and_overlays_render(self):
        for mode in ('solo', 'coop'):
            self.app.mode = mode
            for index in range(9):
                self.app.load_level(index, preview=True)
                self.app.draw()
            for state in (State.LOST, State.WON):
                self.app.game.state = state
                self.app.draw()
            self.app.levels()
            self.app.draw()

    def test_sequential_unlock_is_enforced_in_both_modes(self):
        for mode in ('solo', 'coop'):
            self.app.levels(mode)
            self.assertFalse(self.app.load_level(1))
            self.assertEqual(self.app.page, 'levels')
            self.app.completed[mode] = [9]
            self.assertFalse(self.app.is_unlocked(1))
            self.app.completed[mode] = [1, 3]
            self.assertTrue(self.app.is_unlocked(1))
            self.assertFalse(self.app.is_unlocked(3))
            self.assertTrue(self.app.load_level(1))

    def test_top_saves_replays_once_per_run_and_sorts(self):
        for seconds, moves in ((20.5, 30), (10.25, 40), (10.25, 20)):
            self.app.load_level(0)
            self.app.game.state = State.WON
            self.app.game.elapsed = seconds
            self.app.game.moves = moves
            self.app.record_win()
            self.app.record_win()
        entries = self.app.scores['solo']['1']
        self.assertEqual([(e['seconds'], e['moves']) for e in entries], [(10.25, 20), (10.25, 40), (20.5, 30)])
        other = Application(progress_path=self.path)
        self.assertEqual(other.scores['solo']['1'], entries)
        self.assertEqual(other.scores['coop'], {})
        self.app.levels()
        self.click('top')
        self.app.draw()
        self.click('rank_next')
        self.assertEqual(self.app.selected, 1)
        self.click('rank_mode')
        self.assertEqual(self.app.mode, 'coop')
        self.app.draw()

    def test_old_progress_is_preserved_but_new_campaign_starts_locked(self):
        self.path.write_text('{"solo": [1, 2, 9], "coop": [1], "profile": "Тест"}', encoding='utf-8')
        other = Application(progress_path=self.path)
        self.assertFalse(other.is_unlocked(1))
        self.assertEqual(other.profile, 'Тест')
        other.save_progress()
        import json
        saved = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(saved['legacy_progress']['solo'], [1, 2, 9])
        self.assertEqual(saved['campaign_version'], 2)

    def test_edit_name_and_cancel(self):
        self.click('name')
        self.app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text='Олег'))
        press(self.app, pygame.K_RETURN)
        self.assertEqual(self.app.profile, 'Олег')
        self.click('name')
        self.app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text='Нове'))
        press(self.app, pygame.K_ESCAPE)
        self.assertEqual(self.app.profile, 'Олег')

    def test_leaving_name_input_with_mouse_restores_normal_controls(self):
        self.click('name')
        self.app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text='Команда'))
        self.click('coop')
        self.assertFalse(self.app.editing_name)
        self.assertEqual(self.app.profile, 'Команда')
        press(self.app, pygame.K_RETURN)
        self.assertEqual(self.app.page, 'play')

    def test_resize_and_ukrainian_font(self):
        self.app.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=100, h=100))
        self.assertEqual(self.app.screen.get_size(), (800, 740))
        self.app.draw()
        self.assertTrue(all(m is not None for m in self.app.font.metrics('ҐґЄєІіЇї')))
