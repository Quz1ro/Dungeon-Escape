"""Пошук безпечного таймінгу з реальними пастками й патрулями."""
from collections import deque
from copy import copy

from dungeon_escape.model import DIRECTIONS, State


def clone(game):
    other = copy(game)
    for name in ('players', 'keys', 'exit_keys', 'finished', 'patrols', 'directions'):
        setattr(other, name, list(getattr(game, name)))
    for name in ('collected', 'opened'):
        setattr(other, name, set(getattr(game, name)))
    return other


def navigate(game, owner, target, allowed):
    if game.players[owner] == target or game.finished[owner]:
        return
    queue = deque([(clone(game), [])])
    visited = set()
    while queue:
        current, actions = queue.popleft()
        key = (current.players[owner], len(actions), tuple(current.keys),
               frozenset(current.collected), frozenset(current.opened))
        if key in visited or len(actions) > 180:
            continue
        visited.add(key)
        for direction in (*DIRECTIONS, None):
            other = clone(current)
            if direction is not None:
                point = other.players[owner]
                if (point[0] + direction[0], point[1] + direction[1]) not in allowed:
                    continue
                other.move(owner, direction)
            other.update(0.15)
            if other.state is State.LOST:
                continue
            sequence = actions + [direction]
            if other.players[owner] == target:
                for action in sequence:
                    if action is not None:
                        game.move(owner, action)
                    game.update(0.15)
                    assert game.state is not State.LOST
                return
            queue.append((other, sequence))
    raise AssertionError(f'Немає безпечного проходу: рівень {game.stage.number}, гравець {owner}, ціль {target}')


def play_stage(game):
    stage = game.stage
    path = stage.solutions[0]
    if stage.switches:
        for owner, target in stage.switches:
            navigate(game, owner, target, set(path[:7]))
        assert game.team_open
        for owner in range(2):
            navigate(game, owner, path[5], set(path[:7]))
        start = 5
    else:
        start = 0
    dangerous = set(stage.hazards)
    for route in stage.routes:
        dangerous.update(route)
    last = start
    for at in range(start + 1, len(path)):
        if path[at] in dangerous:
            continue
        segment = set(path[last:at + 1])
        allowed = set(segment)
        for x, y in segment:
            for dx, dy in DIRECTIONS:
                point = x + dx, y + dy
                if point not in path and stage.rows[point[1]][point[0]] == '.':
                    allowed.add(point)
        order = list(range(len(game.players)))
        for owner, pos in stage.doors:
            if pos == path[at] and len(order) == 2:
                order = [owner, 1 - owner]
        for owner in order:
            if not game.finished[owner]:
                navigate(game, owner, path[at], allowed)
        last = at
    assert game.state is State.WON
    return game
