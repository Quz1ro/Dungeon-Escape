"""Віконний інтерфейс Pygame; малювання фігурами без зовнішніх ресурсів."""

import argparse
import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from .levels import LEVELS
from .model import Game, State

CELL = 44
TOP = 100
BOTTOM = 110
BACKGROUND = (15, 20, 34)
FLOOR = (30, 40, 57)
WALL = (64, 78, 103)
TEXT = (235, 241, 250)
MUTED = (166, 181, 205)
BLUE = (83, 193, 241)
GOLD = (255, 207, 88)
RED = (243, 105, 113)
GREEN = (107, 219, 157)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Навчальні прототипи Dungeon Escape")
    parser.add_argument("--prototype", choices=LEVELS, default="03", help="Номер прототипу")
    parser.add_argument("--smoke-test", action="store_true", help="Перевірити цикл і завершити")
    parser.add_argument("--screenshot", type=Path, help="Зберегти знімок ігрового поля PNG")
    return parser


class Application:
    def __init__(self, prototype: str) -> None:
        # Звук не використовується: ініціалізуємо лише потрібні підсистеми.
        pygame.display.init()
        pygame.font.init()
        pygame.key.set_repeat(180, 130)
        self.game = Game(LEVELS[prototype])
        level = self.game.level
        self.screen = pygame.display.set_mode((level.width * CELL, level.height * CELL + TOP + BOTTOM))
        pygame.display.set_caption(f"Dungeon Escape | {level.title}")
        # Вбудований шрифт Pygame містить українську кирилицю.
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 32)
        self.clock = pygame.time.Clock()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.game.quit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.quit()
            elif self.game.state is State.EXIT:
                return
            elif event.key == pygame.K_RETURN:
                self.game.start()
            elif event.key == pygame.K_r and self.game.state is not State.MENU:
                self.game.reset()
            else:
                direction = {
                    pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
                    pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
                    pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
                    pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
                }.get(event.key)
                if direction is not None:
                    self.game.move(direction)

    def label(self, text: str, xy: tuple[int, int], color: tuple = TEXT, title: bool = False) -> None:
        font = self.title_font if title else self.font
        self.screen.blit(font.render(text, True, color), xy)

    def draw(self) -> None:
        game = self.game
        self.screen.fill(BACKGROUND)
        self.label(game.level.title, (18, 14), title=True)
        self.label(game.level.description, (18, 49), MUTED)
        self.label(f"Ключ: {'знайдено' if game.has_key else 'немає'}", (18, 76), GOLD)
        for y, row in enumerate(game.level.rows):
            for x, tile in enumerate(row):
                rect = pygame.Rect(x * CELL + 1, TOP + y * CELL + 1, CELL - 2, CELL - 2)
                pygame.draw.rect(self.screen, WALL if tile == "#" else FLOOR, rect, border_radius=5)
                center = rect.center
                if tile == "X":
                    color = GREEN if game.has_key else MUTED
                    pygame.draw.rect(self.screen, color, rect.inflate(-14, -8), width=3)
                    self.label("В", (center[0] - 6, center[1] - 8), color)
                elif tile == "K" and not game.has_key:
                    pygame.draw.circle(self.screen, GOLD, (center[0] - 6, center[1]), 7, width=3)
                    pygame.draw.line(self.screen, GOLD, (center[0], center[1]), (center[0] + 12, center[1]), 4)
                    pygame.draw.line(self.screen, GOLD, (center[0] + 10, center[1]), (center[0] + 10, center[1] + 7), 3)
        for x, y in game.level.enemy_route:
            pygame.draw.circle(self.screen, (112, 76, 88), (x * CELL + CELL // 2, TOP + y * CELL + CELL // 2), 3)
        if game.enemy is not None:
            x, y = game.enemy
            rect = pygame.Rect(x * CELL + 10, TOP + y * CELL + 10, CELL - 20, CELL - 20)
            pygame.draw.rect(self.screen, RED, rect, border_radius=4)
        x, y = game.player
        pygame.draw.circle(self.screen, BLUE, (x * CELL + CELL // 2, TOP + y * CELL + CELL // 2), 13)
        footer_y = TOP + game.level.height * CELL + 12
        self.label(game.message, (18, footer_y))
        self.label("Стрілки / WASD — рух   ·   R — спочатку   ·   Esc — вихід", (18, footer_y + 30), MUTED)
        self.label("Коло — гравець   ·   Квадрат — ворог   ·   В — вихід", (18, footer_y + 58), MUTED)
        if game.state in (State.MENU, State.WON, State.LOST):
            shade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            shade.fill((8, 13, 25, 222))
            self.screen.blit(shade, (0, 0))
            heading, hint, color = {
                State.MENU: ("Dungeon Escape", "Enter — почати гру", BLUE),
                State.WON: ("Перемога!", "R — зіграти ще раз", GREEN),
                State.LOST: ("Вас упіймали!", "R — спробувати ще раз", RED),
            }[game.state]
            cx, cy = self.screen.get_rect().center
            for text, offset, font, tint in (
                (heading, -65, self.title_font, color),
                (game.level.title, -22, self.font, TEXT),
                (hint, 17, self.font, TEXT),
                ("Esc — закрити", 50, self.font, MUTED),
            ):
                rendered = font.render(text, True, tint)
                self.screen.blit(rendered, rendered.get_rect(center=(cx, cy + offset)))
        pygame.display.flip()

    def run(self, smoke_test: bool = False, screenshot: Path | None = None) -> int:
        if smoke_test:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        frames = 0
        while self.game.state is not State.EXIT:
            seconds = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.game.update(seconds)
            if self.game.state is State.EXIT:
                break
            self.draw()
            frames += 1
            if smoke_test and frames >= 8:
                assert self.game.state is State.PLAYING, "Прототип не перейшов до гри"
                if screenshot is not None:
                    screenshot.parent.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(self.screen, str(screenshot))
                pygame.event.post(pygame.event.Event(pygame.QUIT))
        if smoke_test:
            print(f"Перевірку пройдено: {self.game.level.title}; кадрів: {frames}; вихід: EXIT")
        return 0


def main(default_prototype: str | None = None) -> int:
    parser = make_parser()
    if default_prototype is not None:
        parser.set_defaults(prototype=default_prototype)
    args = parser.parse_args()
    try:
        return Application(args.prototype).run(args.smoke_test, args.screenshot)
    finally:
        pygame.quit()
