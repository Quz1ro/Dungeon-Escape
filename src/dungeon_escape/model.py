"""Детермінована логіка гри без залежності від графічного інтерфейсу."""

from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
import math

Position = tuple[int, int]
DIRECTIONS: tuple[Position, ...] = ((0, -1), (0, 1), (-1, 0), (1, 0))


class State(Enum):
    MENU = auto()
    PLAYING = auto()
    WON = auto()
    LOST = auto()
    EXIT = auto()


@dataclass(frozen=True)
class Level:
    """Карта: # — стіна, . — підлога, P — старт, K — ключ, X — вихід."""

    title: str
    description: str
    rows: tuple[str, ...]
    enemy_route: tuple[Position, ...] = ()
    enemy_interval: float = 0.65

    def __post_init__(self) -> None:
        if len(self.rows) < 3 or len(self.rows[0]) < 3:
            raise ValueError("Карта має бути не меншою за 3 × 3 клітинки")
        if any(len(row) != self.width for row in self.rows):
            raise ValueError("Усі рядки карти повинні мати однакову ширину")
        if set("".join(self.rows)) - set("#.PKX"):
            raise ValueError("Карта містить невідомий символ")
        if any("".join(self.rows).count(marker) != 1 for marker in "PKX"):
            raise ValueError("Карта повинна містити рівно по одному P, K та X")
        if any(tile != "#" for tile in self.rows[0] + self.rows[-1]):
            raise ValueError("Верхня та нижня межі мають бути стінами")
        if any(row[0] != "#" or row[-1] != "#" for row in self.rows):
            raise ValueError("Бічні межі мають бути стінами")
        if not math.isfinite(self.enemy_interval) or self.enemy_interval <= 0:
            raise ValueError("Інтервал руху ворога має бути скінченним і додатним")
        reachable = self.reachable_from(self.locate("P"))
        if not {self.locate("K"), self.locate("X")}.issubset(reachable):
            raise ValueError("Гравець повинен мати шлях до ключа та виходу")
        if self.enemy_route:
            if len(self.enemy_route) < 2:
                raise ValueError("Маршрут патруля потребує щонайменше двох клітинок")
            if self.enemy_route[0] == self.locate("P"):
                raise ValueError("Ворог не може починати на клітинці гравця")
            if any(point not in reachable for point in self.enemy_route):
                raise ValueError("Маршрут ворога повинен проходити доступною підлогою")
            for first, second in zip(self.enemy_route, self.enemy_route[1:]):
                if abs(first[0] - second[0]) + abs(first[1] - second[1]) != 1:
                    raise ValueError("Сусідні точки маршруту мають бути суміжними")

    @property
    def width(self) -> int:
        return len(self.rows[0])

    @property
    def height(self) -> int:
        return len(self.rows)

    def locate(self, marker: str) -> Position:
        for y, row in enumerate(self.rows):
            if marker in row:
                return row.index(marker), y
        raise ValueError(f"На карті немає символу {marker}")

    def passable(self, point: Position) -> bool:
        x, y = point
        return 0 <= x < self.width and 0 <= y < self.height and self.rows[y][x] != "#"

    def reachable_from(self, start: Position) -> set[Position]:
        visited = {start}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in DIRECTIONS:
                neighbor = x + dx, y + dy
                if neighbor not in visited and self.passable(neighbor):
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited


class Game:
    """Гравець рухається по клітинках; ворог патрулює туди й назад за таймером."""

    def __init__(self, level: Level) -> None:
        self.level = level
        self.reset(State.MENU)

    def reset(self, state: State = State.PLAYING) -> None:
        self.state = state
        self.player = self.level.locate("P")
        self.has_key = False
        self.enemy_index = 0
        self.enemy_direction = 1
        self.enemy_elapsed = 0.0
        self.message = "Знайдіть ключ і дістаньтеся виходу."

    @property
    def enemy(self) -> Position | None:
        route = self.level.enemy_route
        return route[self.enemy_index] if route else None

    def start(self) -> None:
        if self.state is State.MENU:
            self.reset()

    def quit(self) -> None:
        self.state = State.EXIT

    def move(self, direction: Position) -> None:
        if self.state is not State.PLAYING or direction not in DIRECTIONS:
            return
        target = self.player[0] + direction[0], self.player[1] + direction[1]
        if not self.level.passable(target):
            return
        self.player = target
        # Зіткнення має пріоритет над ключем і перемогою.
        if self._check_enemy_collision():
            return
        if self.player == self.level.locate("K") and not self.has_key:
            self.has_key = True
            self.message = "Ключ знайдено! Тепер прямуйте до виходу."
        if self.player == self.level.locate("X"):
            if self.has_key:
                self.state = State.WON
                self.message = "Ви вибралися з підземелля!"
            else:
                self.message = "Вихід замкнено. Спершу знайдіть ключ."

    def update(self, seconds: float) -> None:
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("Час кадру має бути скінченним і невід’ємним")
        if self.state is not State.PLAYING or not self.level.enemy_route:
            return
        self.enemy_elapsed += seconds
        # Цикл враховує кілька кроків ворога протягом довгого кадру.
        while self.enemy_elapsed >= self.level.enemy_interval:
            self.enemy_elapsed -= self.level.enemy_interval
            next_index = self.enemy_index + self.enemy_direction
            if not 0 <= next_index < len(self.level.enemy_route):
                self.enemy_direction *= -1
                next_index = self.enemy_index + self.enemy_direction
            self.enemy_index = next_index
            if self._check_enemy_collision():
                break

    def _check_enemy_collision(self) -> bool:
        if self.player == self.enemy:
            self.state = State.LOST
            self.message = "Вас упіймав охоронець. Спробуйте ще раз."
            return True
        return False
