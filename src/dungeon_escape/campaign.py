"""Дев’ять лабіринтів для одного гравця та дев’ять для двох."""
from collections import deque
from dataclasses import dataclass
import math
import random

from .model import DIRECTIONS, State


@dataclass(frozen=True)
class Stage:
    number: int
    rows: tuple[str, ...]
    starts: tuple[tuple[int, int], ...]
    exits: tuple[tuple[int, int], ...]
    door_keys: tuple[tuple[int, tuple[int, int]], ...]
    doors: tuple[tuple[int, tuple[int, int]], ...]
    exit_keys: tuple[tuple[int, int], ...]
    routes: tuple[tuple[tuple[int, int], ...], ...]
    solutions: tuple[tuple[tuple[int, int], ...], ...]
    interval: float

    @property
    def width(self):
        return len(self.rows[0])

    @property
    def height(self):
        return len(self.rows)

    @property
    def distance(self):
        return len(self.solutions[0]) - 1


def maze(seed):
    rng = random.Random(seed)
    rows = [['#'] * 13 for _ in range(17)]
    start = (1, 1)
    rows[1][1] = '.'
    stack = [start]
    while stack:
        x, y = stack[-1]
        choices = [(x + dx * 2, y + dy * 2) for dx, dy in DIRECTIONS
                   if 0 < x + dx * 2 < 12 and 0 < y + dy * 2 < 16
                   and rows[y + dy * 2][x + dx * 2] == '#']
        if not choices:
            stack.pop()
            continue
        nx, ny = rng.choice(choices)
        rows[(y + ny) // 2][(x + nx) // 2] = '.'
        rows[ny][nx] = '.'
        stack.append((nx, ny))
    parents = {start: None}
    queue = deque([start])
    last = start
    while queue:
        last = queue.popleft()
        for dx, dy in DIRECTIONS:
            p = last[0] + dx, last[1] + dy
            if rows[p[1]][p[0]] == '.' and p not in parents:
                parents[p] = last
                queue.append(p)
    path = []
    while last is not None:
        path.append(last)
        last = parents[last]
    path.reverse()
    # Патрулі охороняють бічні проходи; основний маршрут залишається прохідним.
    available = set(parents) - set(path)
    routes = []
    for point in sorted(available):
        if point not in available:
            continue
        route = [point]
        while len(route) < 4:
            x, y = route[-1]
            neighbors = [(x + dx, y + dy) for dx, dy in DIRECTIONS
                         if (x + dx, y + dy) in available and (x + dx, y + dy) not in route]
            if not neighbors:
                break
            route.append(neighbors[0])
        if len(route) >= 2:
            routes.append(tuple(route))
            available.difference_update(route)
    return tuple(''.join(row) for row in rows), tuple(path), tuple(routes)


def build_stages(players):
    candidates = {}
    for seed in range(160):
        rows, path, routes = maze(seed)
        if len(routes) >= 3:
            candidates.setdefault(len(path), (rows, path, routes))
    lengths = sorted(candidates)
    if len(lengths) < 9:
        raise ValueError('Недостатньо різних рівнів складності')
    result = []
    for index in range(9):
        rows, path, routes = candidates[lengths[index * (len(lengths) - 1) // 8]]
        combined = rows if players == 1 else tuple(row + '#' + row[::-1] for row in rows)
        starts, exits, keys, doors, final_keys, paths, patrols = [], [], [], [], [], [], []
        gate_count = 1 + index // 3
        for owner in range(players):
            def transform(point):
                return point if owner == 0 else (26 - point[0], point[1])
            own_path = tuple(map(transform, path))
            paths.append(own_path)
            starts.append(own_path[0])
            exits.append(own_path[-1])
            final_keys.append(own_path[-3])
            for gate in range(gate_count):
                at = (gate + 1) * (len(path) - 8) // (gate_count + 1)
                keys.append((owner, own_path[at - 2]))
                doors.append((owner, own_path[at]))
            for route in routes[:min(3, (index + 2) // 3)]:
                patrols.append(tuple(map(transform, route)))
        result.append(Stage(index + 1, combined, tuple(starts), tuple(exits), tuple(keys),
                            tuple(doors), tuple(final_keys), tuple(patrols), tuple(paths),
                            0.85 - index * 0.065))
    return tuple(result)


SOLO_STAGES = build_stages(1)
COOP_STAGES = build_stages(2)


class Session:
    def __init__(self, stage):
        self.stage = stage
        self.reset()

    def reset(self):
        self.state = State.PLAYING
        self.players = list(self.stage.starts)
        self.keys = [0] * len(self.players)
        self.exit_keys = [False] * len(self.players)
        self.finished = [False] * len(self.players)
        self.collected = set()
        self.opened = set()
        self.patrols = [0] * len(self.stage.routes)
        self.directions = [1] * len(self.patrols)
        self.elapsed = 0.0
        self.timer = 0.0
        self.moves = 0
        self.message = 'Круглий ключ — для дверей, ромб — для виходу.'

    @property
    def enemies(self):
        return [route[self.patrols[i]] for i, route in enumerate(self.stage.routes)]

    def collision(self):
        if any(not self.finished[i] and pos in self.enemies for i, pos in enumerate(self.players)):
            self.state = State.LOST
            self.message = 'Охоронець упіймав гравця. R — повторити.'
            return True
        return False

    def move(self, owner, direction):
        if self.state is not State.PLAYING or self.finished[owner] or direction not in DIRECTIONS:
            return
        x, y = self.players[owner]
        target = x + direction[0], y + direction[1]
        if not (0 <= target[0] < self.stage.width and 0 <= target[1] < self.stage.height):
            return
        if self.stage.rows[target[1]][target[0]] == '#':
            return
        for gate, (gate_owner, pos) in enumerate(self.stage.doors):
            if pos == target and gate not in self.opened:
                if gate_owner != owner or self.keys[owner] == 0:
                    self.message = 'Потрібен круглий ключ відповідного кольору.'
                    return
                self.keys[owner] -= 1
                self.opened.add(gate)
        self.players[owner] = target
        self.moves += 1
        if self.collision():
            return
        for key, (key_owner, pos) in enumerate(self.stage.door_keys):
            if key_owner == owner and pos == target and key not in self.collected:
                self.collected.add(key)
                self.keys[owner] += 1
                self.message = f'Гравець {owner + 1}: ключ від дверей знайдено.'
        if target == self.stage.exit_keys[owner]:
            self.exit_keys[owner] = True
            self.message = f'Гравець {owner + 1}: ключ виходу знайдено.'
        if target == self.stage.exits[owner]:
            if self.exit_keys[owner]:
                self.finished[owner] = True
                self.message = f'Гравець {owner + 1} дістався виходу. Чекаємо напарника.'
                if all(self.finished):
                    self.state = State.WON
                    self.message = 'Рівень пройдено!'
            else:
                self.message = 'Для виходу потрібен ключ-ромб вашого кольору.'

    def update(self, dt):
        if not math.isfinite(dt) or dt < 0:
            raise ValueError('Некоректний час кадру')
        if self.state is not State.PLAYING:
            return
        self.elapsed += dt
        self.timer += dt
        if not self.stage.routes:
            self.timer = 0
            return
        while self.timer >= self.stage.interval:
            self.timer -= self.stage.interval
            for i, route in enumerate(self.stage.routes):
                nxt = self.patrols[i] + self.directions[i]
                if not 0 <= nxt < len(route):
                    self.directions[i] *= -1
                    nxt = self.patrols[i] + self.directions[i]
                self.patrols[i] = nxt
                if self.collision():
                    return
