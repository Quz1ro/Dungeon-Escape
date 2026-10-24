"""Перевірки правил, меж карти та досяжності перемоги у трьох прототипах."""

from collections import deque
from copy import copy
from dataclasses import replace
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dungeon_escape.levels import LEVELS
from dungeon_escape.model import DIRECTIONS, Game, Level, State

SMALL = Level("Тест", "Кімната", ("#######", "#P.K.X#", "#.....#", "#######"))


def winning_actions(level: Level) -> list[tuple[int, int] | None]:
    """Пошук у просторі (гравець, ключ, позиція й напрям патруля).

    Одна дія — крок або очікування; після неї ворог робить один крок.
    Це свідок прохідності за конкретного темпу, а не оцінка складності.
    """
    game = Game(level)
    game.start()
    queue = deque([(game, [])])
    visited = set()
    while queue:
        current, actions = queue.popleft()
        key = (current.player, current.has_key, current.enemy_index, current.enemy_direction)
        if key in visited:
            continue
        visited.add(key)
        for action in (*DIRECTIONS, None):
            candidate = copy(current)
            if action is not None:
                candidate.move(action)
            candidate.update(level.enemy_interval)
            if candidate.state is State.WON:
                return actions + [action]
            if candidate.state is State.PLAYING:
                queue.append((candidate, actions + [action]))
    raise AssertionError(f"Не знайдено шлях до перемоги: {level.title}")


class GameRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game(SMALL)
        self.game.start()

    def test_menu_freezes_simulation(self):
        game = Game(LEVELS["02"])
        before = (game.player, game.enemy)
        game.move((1, 0))
        game.update(10)
        self.assertEqual(game.state, State.MENU)
        self.assertEqual((game.player, game.enemy), before)

    def test_wall_blocks_movement(self):
        self.game.move((0, -1))
        self.assertEqual(self.game.player, (1, 1))

    def test_no_diagonal_or_teleport(self):
        for direction in ((1, 1), (2, 0), (0, 0)):
            self.game.move(direction)
        self.assertEqual(self.game.player, (1, 1))

    def test_key_disappears_logically_and_opens_exit(self):
        self.game.move((1, 0))
        self.game.move((1, 0))
        self.assertTrue(self.game.has_key)
        self.game.move((1, 0))
        self.game.move((1, 0))
        self.assertEqual(self.game.state, State.WON)

    def test_locked_exit_does_not_win_or_trap_player(self):
        self.game.move((0, 1))
        for _ in range(4):
            self.game.move((1, 0))
        self.game.move((0, -1))
        self.assertEqual(self.game.player, SMALL.locate("X"))
        self.assertEqual(self.game.state, State.PLAYING)
        self.assertFalse(self.game.has_key)
        self.assertIn("замкнено", self.game.message)
        self.game.move((-1, 0))
        self.assertEqual(self.game.player, (4, 1))

    def test_key_is_kept_after_leaving_its_tile(self):
        for direction in ((1, 0), (1, 0), (-1, 0)):
            self.game.move(direction)
        self.assertTrue(self.game.has_key)

    def test_player_walks_into_enemy(self):
        game = Game(replace(SMALL, enemy_route=((2, 1), (3, 1))))
        game.start()
        game.move((1, 0))
        self.assertEqual(game.state, State.LOST)

    def test_collision_has_priority_over_key(self):
        game = Game(replace(SMALL, enemy_route=((3, 1), (4, 1))))
        game.start()
        game.move((1, 0))
        game.move((1, 0))
        self.assertEqual(game.state, State.LOST)
        self.assertFalse(game.has_key)

    def test_collision_has_priority_over_exit(self):
        game = Game(replace(SMALL, enemy_route=((5, 1), (4, 1))))
        game.start()
        for _ in range(4):
            game.move((1, 0))
        self.assertTrue(game.has_key)
        self.assertEqual(game.state, State.LOST)

    def test_enemy_moves_by_time_and_bounces(self):
        game = Game(replace(SMALL, enemy_route=((2, 2), (3, 2), (4, 2)), enemy_interval=0.5))
        game.start()
        game.update(0.25)
        self.assertEqual(game.enemy, (2, 2))
        game.update(0.25)
        self.assertEqual(game.enemy, (3, 2))
        game.update(1.0)
        self.assertEqual(game.enemy, (3, 2))
        self.assertEqual(game.enemy_direction, -1)

    def test_enemy_hits_player_and_long_frame_stops_at_collision(self):
        game = Game(replace(SMALL, enemy_route=((2, 1), (1, 1)), enemy_interval=0.5))
        game.start()
        game.update(2.0)
        self.assertEqual(game.state, State.LOST)
        self.assertEqual(game.enemy, game.player)

    def test_equivalent_elapsed_time_produces_same_patrol_position(self):
        level = replace(SMALL, enemy_route=((2, 2), (3, 2), (4, 2)), enemy_interval=0.5)
        first, second = Game(level), Game(level)
        first.start()
        second.start()
        first.update(2.5)
        for _ in range(10):
            second.update(0.25)
        self.assertEqual(first.enemy, second.enemy)
        self.assertEqual(first.enemy_direction, second.enemy_direction)

    def test_restart_restores_all_mutable_state(self):
        game = Game(replace(SMALL, enemy_route=((2, 2), (3, 2))))
        game.start()
        game.move((1, 0))
        game.move((1, 0))
        game.update(1)
        game.reset()
        self.assertEqual(game.state, State.PLAYING)
        self.assertEqual(game.player, SMALL.locate("P"))
        self.assertFalse(game.has_key)
        self.assertEqual(game.enemy, (2, 2))
        self.assertEqual(game.enemy_elapsed, 0)
        self.assertEqual(game.enemy_direction, 1)

    def test_terminal_states_freeze_movement_and_timer(self):
        for state in (State.WON, State.LOST, State.EXIT):
            with self.subTest(state=state):
                game = Game(LEVELS["02"])
                game.reset(state)
                before = (game.player, game.enemy, game.enemy_elapsed)
                game.move((1, 0))
                game.update(5)
                game.start()
                self.assertEqual(game.state, state)
                self.assertEqual((game.player, game.enemy, game.enemy_elapsed), before)

    def test_quit_from_every_active_state(self):
        for state in (State.MENU, State.PLAYING, State.WON, State.LOST):
            self.game.reset(state)
            self.game.quit()
            self.assertEqual(self.game.state, State.EXIT)

    def test_invalid_elapsed_time_rejected(self):
        for seconds in (-1, math.inf, math.nan):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                self.game.update(seconds)

    def test_all_prototypes_have_a_winning_playthrough(self):
        for number, level in LEVELS.items():
            with self.subTest(prototype=number):
                game = Game(level)
                game.start()
                for action in winning_actions(level):
                    if action is not None:
                        game.move(action)
                    game.update(level.enemy_interval)
                self.assertEqual(game.state, State.WON)
                self.assertTrue(game.has_key)
                self.assertEqual(game.player, level.locate("X"))


class MapValidationTests(unittest.TestCase):
    def test_outside_map_is_not_passable(self):
        for point in ((-1, 1), (1, -1), (SMALL.width, 1), (1, SMALL.height)):
            self.assertFalse(SMALL.passable(point))

    def test_bad_maps_rejected(self):
        invalid_maps = (
            (),
            ("###", "#P#", "###"),
            ("#######", "#P.K.X", "#######"),
            ("#######", "#P?K.X#", "#######"),
            ("#######", "#PPK.X#", "#######"),
            ("#######", "#P#K#X#", "#######"),
            ("#.#####", "#P.K.X#", "#######"),
            ("#######", ".P.K.X#", "#######"),
        )
        for rows in invalid_maps:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                replace(SMALL, rows=rows)

    def test_bad_routes_rejected(self):
        for route in (((2, 1),), ((1, 1), (2, 1)), ((0, 0), (1, 0)), ((2, 1), (4, 1))):
            with self.subTest(route=route), self.assertRaises(ValueError):
                replace(SMALL, enemy_route=route)

    def test_invalid_patrol_intervals_rejected(self):
        for interval in (0, -1, math.inf, math.nan):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                replace(SMALL, enemy_interval=interval)


if __name__ == "__main__":
    unittest.main()
