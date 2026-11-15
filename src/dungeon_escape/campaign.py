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
    switches: tuple[tuple[int, tuple[int, int]], ...] = ()
    team_gate: tuple[int, int] | None = None
    hazards: tuple[tuple[int, int], ...] = ()
    hazard_period: float = 3.0

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
        rows, path, _ = maze(seed)
        candidates.setdefault(len(path), (rows, path))
    lengths = sorted(candidates)
    result = []
    for index in range(9):
        original, path = candidates[lengths[index * (len(lengths) - 1) // 8]]
        rows = [list(row) for row in original]
        starts = (path[0],) if players == 1 else (path[0], path[1])
        exits = (path[-1],) if players == 1 else (path[-1], path[-2])
        final_keys = (path[-3],) if players == 1 else (path[-5], path[-3])
        switches = () if players == 1 else ((0, path[3]), (1, path[5]))
        team_gate = None if players == 1 else path[7]
        keys, doors = [], []
        gate_count = (1 if players == 1 else 2) + index // 3
        for gate in range(gate_count):
            at = 12 + (gate + 1) * (len(path) - 20) // (gate_count + 1)
            owner = gate % players
            keys.append((owner, path[at - 2]))
            doors.append((owner, path[at]))
        reserved = set(starts + exits + final_keys)
        reserved.update(p for _, p in (*keys, *doors, *switches))
        if team_gate:
            reserved.add(team_gate)
        patrols = []
        # Охоронці перетинають обов’язковий шлях. Поряд є ніша для ухилення.
        used = set()
        target_count = 1 + index // 3
        centers = sorted(range(10, len(path) - 7), key=lambda n: abs(n - len(path) // 2))
        for at in centers:
            route = path[at - 1:at + 2]
            if set(route) & (reserved | used):
                continue
            x, y = path[at]
            shelter = None
            for dx, dy in DIRECTIONS:
                point = x + dx, y + dy
                if not (0 < point[0] < 12 and 0 < point[1] < 16) or point in path:
                    continue
                if rows[point[1]][point[0]] == '.':
                    shelter = point
                    break
                neighbors = [(point[0] + ax, point[1] + ay) for ax, ay in DIRECTIONS]
                if sum(rows[ny][nx] == '.' for nx, ny in neighbors) == 1:
                    shelter = point
                    break
            if shelter is None:
                continue
            rows[shelter[1]][shelter[0]] = '.'
            patrols.append(tuple(route))
            used.update(path[max(0, at - 4):at + 5])
            if len(patrols) == target_count:
                break
        if not patrols:
            raise ValueError('На карті немає місця для патруля з укриттям')
        free = [p for p in path[9:-6] if p not in reserved | used]
        count = min(1 + index // 2, len(free))
        hazards = tuple(free[i * len(free) // count] for i in range(count))
        solutions = (tuple(path),) * players
        result.append(Stage(index + 1, tuple(''.join(row) for row in rows), starts, exits,
                            tuple(keys), tuple(doors), final_keys, tuple(patrols), solutions,
                            0.75 - index * 0.05, switches, team_gate, hazards, 3.0 - index * 0.1))
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
        self.team_open = self.stage.team_gate is None
        self.message = 'Станьте разом на кольорові плити, щоб відкрити спільні ворота.' if self.stage.switches else 'Обережно: червоні пастки активні, помаранчеві попереджають.'

    @property
    def enemies(self):
        return [route[self.patrols[i]] for i, route in enumerate(self.stage.routes)]

    def hazard_active(self, at=None):
        return (self.elapsed if at is None else at) % self.stage.hazard_period < self.stage.hazard_period * 0.5

    def check_switches(self):
        if self.stage.switches and all(self.players[owner] == pos for owner, pos in self.stage.switches):
            self.team_open = True
            self.message = 'Спільні ворота відкриті! Далі відкривайте двері по черзі.'

    def collision(self):
        if any(not self.finished[i] and pos in self.enemies for i, pos in enumerate(self.players)):
            self.state = State.LOST
            self.message = 'Охоронець упіймав гравця. R — повторити.'
            return True
        if self.hazard_active() and any(not self.finished[i] and pos in self.stage.hazards for i, pos in enumerate(self.players)):
            self.state = State.LOST
            self.message = 'Активна пастка! Дочекайтеся безпечної фази. R — повторити.'
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
        if target == self.stage.team_gate and not self.team_open:
            self.message = 'Обидва гравці мають одночасно стати на свої плити.'
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
        self.check_switches()
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
        remaining = dt
        while remaining > 0:
            step = min(remaining, 0.025)
            remaining = max(0.0, remaining - step)
            self.elapsed += step
            self.timer += step
            if self.collision():
                return
            while self.stage.routes and self.timer + 1e-9 >= self.stage.interval:
                self.timer -= self.stage.interval
                for i, route in enumerate(self.stage.routes):
                    nxt = self.patrols[i] + self.directions[i]
                    if not 0 <= nxt < len(route):
                        self.directions[i] *= -1
                        nxt = self.patrols[i] + self.directions[i]
                    self.patrols[i] = nxt
                    if self.collision():
                        return
