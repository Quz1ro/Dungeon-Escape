"""Правила особистих ключів, спільної перемоги та прохідність 18 карт."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from dungeon_escape.campaign import SOLO_STAGES, COOP_STAGES, Session, Stage
from dungeon_escape.model import State
from playthrough import play_stage

ROOM = Stage(1, ('#########', '#.......#', '#.......#', '#.......#', '#########'),
             ((1, 1), (1, 3)), ((7, 1), (7, 3)),
             ((0, (2, 1)), (1, (2, 3))), ((0, (3, 1)), (1, (3, 3))),
             ((5, 1), (5, 3)), (), (), 0.5)


def finish_player(game, owner, path):
    for before, after in zip(path, path[1:]):
        game.move(owner, (after[0] - before[0], after[1] - before[1]))
        game.update(0.17)


class CampaignTests(unittest.TestCase):
    def test_all_eighteen_stages_have_legal_winning_routes(self):
        for stages in (SOLO_STAGES, COOP_STAGES):
            self.assertEqual(len(stages), 9)
            for stage in stages:
                with self.subTest(players=len(stage.starts), level=stage.number):
                    game = Session(stage)
                    play_stage(game)
                    self.assertEqual(game.state, State.WON)
                    self.assertTrue(all(game.exit_keys))
                    self.assertEqual(len(game.opened), len(stage.doors))
                    self.assertTrue(all(game.finished))

    def test_difficulty_increases_on_every_stage(self):
        for stages in (SOLO_STAGES, COOP_STAGES):
            for previous, following in zip(stages, stages[1:]):
                self.assertGreater(following.distance, previous.distance)
                self.assertLess(following.interval, previous.interval)
                self.assertGreaterEqual(len(following.doors), len(previous.doors))
                self.assertGreaterEqual(len(following.routes), len(previous.routes))

    def test_objects_do_not_overlap_and_patrols_are_valid(self):
        for stage in (*SOLO_STAGES, *COOP_STAGES):
            objects = [*stage.starts, *stage.exits, *stage.exit_keys,
                       *(p for _, p in stage.doors), *(p for _, p in stage.door_keys)]
            self.assertEqual(len(objects), len(set(objects)))
            for route in stage.routes:
                for p in route:
                    self.assertEqual(stage.rows[p[1]][p[0]], '.')
                for a, b in zip(route, route[1:]):
                    self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)

    def test_matching_key_is_consumed_and_gate_stays_open(self):
        game = Session(ROOM)
        game.move(0, (1, 0))
        self.assertEqual(game.keys, [1, 0])
        game.move(0, (1, 0))
        self.assertEqual(game.keys, [0, 0])
        self.assertIn(0, game.opened)
        game.move(0, (-1, 0))
        game.move(0, (1, 0))
        self.assertEqual(game.players[0], (3, 1))
        self.assertEqual(game.keys[0], 0)

    def test_gate_blocks_without_key(self):
        game = Session(ROOM)
        game.players[0] = (4, 1)
        game.move(0, (-1, 0))
        self.assertEqual(game.players[0], (4, 1))
        self.assertFalse(game.opened)

    def test_cannot_take_other_players_keys_or_open_their_gate(self):
        game = Session(ROOM)
        game.players[1] = (1, 1)
        game.move(1, (1, 0))
        self.assertFalse(game.collected)
        game.keys[1] = 1
        game.move(1, (1, 0))
        self.assertEqual(game.players[1], (2, 1))
        self.assertEqual(game.keys[1], 1)
        game.players[1] = (4, 1)
        game.move(1, (1, 0))
        self.assertFalse(game.exit_keys[1])

    def test_exit_requires_personal_final_key(self):
        game = Session(ROOM)
        game.players[0] = (6, 1)
        game.move(0, (1, 0))
        self.assertFalse(game.finished[0])
        self.assertEqual(game.state, State.PLAYING)

    def test_joint_win_waits_for_second_player(self):
        game = Session(ROOM)
        for _ in range(6):
            game.move(0, (1, 0))
        self.assertTrue(game.finished[0])
        self.assertEqual(game.state, State.PLAYING)
        game.move(0, (-1, 0))
        self.assertEqual(game.players[0], (7, 1))
        for _ in range(6):
            game.move(1, (1, 0))
        self.assertEqual(game.state, State.WON)

    def test_patrol_collision_loses_whole_attempt(self):
        game = Session(COOP_STAGES[8])
        game.players[1] = game.stage.routes[0][1]
        game.update(game.stage.interval)
        self.assertEqual(game.state, State.LOST)
        before = list(game.players)
        game.move(0, (1, 0))
        game.update(100)
        self.assertEqual(game.players, before)

    def test_restart_clears_both_inventories_and_timers(self):
        game = Session(ROOM)
        game.move(0, (1, 0))
        game.move(0, (1, 0))
        game.move(1, (1, 0))
        game.update(0.2)
        game.reset()
        self.assertEqual(game.players, list(ROOM.starts))
        self.assertEqual(game.keys, [0, 0])
        self.assertFalse(any(game.exit_keys))
        self.assertFalse(game.collected)
        self.assertFalse(game.opened)
        self.assertEqual(game.elapsed, 0)

    def test_walls_and_invalid_directions_do_not_move_players(self):
        game = Session(ROOM)
        for direction in ((0, -1), (-1, 0), (1, 1), (2, 0)):
            game.move(0, direction)
        self.assertEqual(game.players[0], ROOM.starts[0])

    def test_running_straight_without_waiting_loses_on_every_solo_level(self):
        for stage in SOLO_STAGES:
            with self.subTest(level=stage.number):
                game = Session(stage)
                finish_player(game, 0, stage.solutions[0])
                self.assertEqual(game.state, State.LOST)

    def test_trap_kills_on_entry_and_when_switching_on_under_player(self):
        stage = SOLO_STAGES[0]
        trap = stage.hazards[0]
        game = Session(stage)
        game.players[0] = trap
        self.assertTrue(game.collision())
        self.assertEqual(game.state, State.LOST)
        game.reset()
        game.elapsed = stage.hazard_period * 0.75
        game.players[0] = trap
        self.assertFalse(game.collision())
        game.update(stage.hazard_period)
        self.assertEqual(game.state, State.LOST)

    def test_shared_map_requires_both_switches_and_alternating_door_owners(self):
        for stage in COOP_STAGES:
            game = Session(stage)
            self.assertEqual(len(stage.rows[0]), 13)
            self.assertEqual({owner for owner, _ in stage.doors}, {0, 1})
            first_owner, first_pos = stage.switches[0]
            game.players[first_owner] = first_pos
            game.check_switches()
            self.assertFalse(game.team_open)
            for owner, pos in stage.switches:
                game.players[owner] = pos
            game.check_switches()
            self.assertTrue(game.team_open)
            game.reset()
            self.assertFalse(game.team_open)

    def test_team_gate_blocks_both_until_switches_are_pressed(self):
        stage = COOP_STAGES[0]
        gate = stage.team_gate
        before = stage.solutions[0][6]
        for owner in (0, 1):
            game = Session(stage)
            game.players[owner] = before
            game.move(owner, (gate[0] - before[0], gate[1] - before[1]))
            self.assertEqual(game.players[owner], before)

    def test_neither_player_can_bypass_partners_locked_doors(self):
        from collections import deque
        from dungeon_escape.model import DIRECTIONS
        for stage in COOP_STAGES:
            for owner in (0, 1):
                blocked = {pos for door_owner, pos in stage.doors if door_owner != owner}
                seen = {stage.starts[owner]}
                queue = deque(seen)
                while queue:
                    x, y = queue.popleft()
                    for dx, dy in DIRECTIONS:
                        point = x + dx, y + dy
                        if point not in seen and point not in blocked and stage.rows[point[1]][point[0]] == '.':
                            seen.add(point)
                            queue.append(point)
                self.assertNotIn(stage.exits[owner], seen)

    def test_invalid_time_is_rejected(self):
        game = Session(ROOM)
        for dt in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                game.update(dt)
