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
    parser = argparse.ArgumentParser(description="Dungeon Escape")
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
        self.level_ids = tuple(LEVELS)
        self.selected = self.level_ids.index(prototype)
        self.game = Game(LEVELS[prototype])
        level = self.game.level
        self.screen = pygame.display.set_mode((level.width * CELL, max(694, level.height * CELL + TOP + BOTTOM)))
        pygame.display.set_caption(f"Dungeon Escape | {level.title}")
        # Вбудований шрифт Pygame містить українську кирилицю.
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 32)
        self.clock = pygame.time.Clock()
        self.icon = self.make_icon()
        pygame.display.set_icon(self.icon)

    @staticmethod
    def make_icon() -> pygame.Surface:
        icon = pygame.Surface((96, 96), pygame.SRCALPHA)
        pygame.draw.rect(icon, (30, 40, 57), (0, 0, 96, 96), border_radius=20)
        pygame.draw.rect(icon, WALL, (17, 12, 62, 73), border_radius=8)
        pygame.draw.rect(icon, BACKGROUND, (28, 25, 40, 60), border_radius=12)
        pygame.draw.circle(icon, GOLD, (43, 49), 10, width=4)
        pygame.draw.line(icon, GOLD, (51, 54), (71, 71), 5)
        pygame.draw.line(icon, GOLD, (64, 64), (59, 70), 5)
        return icon

    def load_level(self, index: int, start: bool = False) -> None:
        self.selected = index % len(self.level_ids)
        self.game = Game(LEVELS[self.level_ids[self.selected]])
        level = self.game.level
        self.screen = pygame.display.set_mode(
            (level.width * CELL, max(694, level.height * CELL + TOP + BOTTOM)))
        pygame.display.set_caption(f"Dungeon Escape | {level.title}")
        if start:
            self.game.start()

    def level_buttons(self) -> list[pygame.Rect]:
        return [pygame.Rect(62, 244 + i * 52, self.screen.get_width() - 124, 44)
                for i in range(len(self.level_ids))]

    def draw_menu(self) -> None:
        self.screen.fill(BACKGROUND)
        cx = self.screen.get_width() // 2
        self.screen.blit(self.icon, (cx - 48, 28))
        title = self.title_font.render("DUNGEON ESCAPE", True, GOLD)
        self.screen.blit(title, title.get_rect(center=(cx, 151)))
        self.label("Знайдіть ключ. Обійдіть охоронця. Відкрийте вихід.", (62, 185), MUTED)
        self.label("ОБЕРІТЬ РІВЕНЬ", (62, 218), BLUE)
        for i, rect in enumerate(self.level_buttons()):
            selected = i == self.selected
            pygame.draw.rect(self.screen, WALL if selected else FLOOR, rect, border_radius=8)
            if selected:
                pygame.draw.rect(self.screen, GOLD, rect, width=2, border_radius=8)
            name = LEVELS[self.level_ids[i]].title.split(" — ", 1)[-1]
            self.label(f"{i + 1}.  {name}", (rect.x + 16, rect.y + 12), GOLD if selected else TEXT)
        self.label("Стрілки — вибір   ·   Enter або клацання — почати", (62, 584), TEXT)
        self.label("M — меню під час гри   ·   Esc — закрити", (62, 615), MUTED)
        pygame.display.flip()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.game.quit()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.game.state is State.MENU:
            for index, rect in enumerate(self.level_buttons()):
                if rect.collidepoint(event.pos):
                    self.load_level(index, start=True)
                    break
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.quit()
            elif self.game.state is State.EXIT:
                return
            elif self.game.state is State.MENU:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.load_level(self.selected - 1)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.load_level(self.selected + 1)
                elif event.key == pygame.K_RETURN:
                    self.game.start()
            elif event.key == pygame.K_m:
                self.load_level(self.selected)
            elif event.key in (pygame.K_n, pygame.K_RETURN) and self.game.state is State.WON:
                if self.selected + 1 < len(self.level_ids):
                    self.load_level(self.selected + 1, start=True)
                else:
                    self.load_level(0)
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
        if game.state is State.MENU:
            self.draw_menu()
            return
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
        self.label("WASD / стрілки · R — спочатку · M — меню · Esc — вихід", (18, footer_y + 30), MUTED)
        self.label("Коло — гравець   ·   Квадрат — ворог   ·   В — вихід", (18, footer_y + 58), MUTED)
        if game.state in (State.MENU, State.WON, State.LOST):
            shade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            shade.fill((8, 13, 25, 222))
            self.screen.blit(shade, (0, 0))
            heading, hint, color = {
                State.MENU: ("Dungeon Escape", "Enter — почати гру", BLUE),
                State.WON: ("Перемога!", "Enter — далі   ·   R — повторити", GREEN),
                State.LOST: ("Вас упіймали!", "R — спробувати ще раз", RED),
            }[game.state]
            cx, cy = self.screen.get_rect().center
            for text, offset, font, tint in (
                (heading, -65, self.title_font, color),
                (game.level.title, -22, self.font, TEXT),
                (hint, 17, self.font, TEXT),
                ("M — меню   ·   Esc — закрити", 50, self.font, MUTED),
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
