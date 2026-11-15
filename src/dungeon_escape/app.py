"""Меню, вибір рівня та локальна гра на одній клавіатурі."""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from .campaign import SOLO_STAGES, COOP_STAGES, Session
from .model import State
from .records import format_time, clean_scores

BG = (15, 20, 34)
PANEL = (29, 39, 56)
WALL = (62, 77, 102)
TEXT = (235, 241, 250)
MUTED = (162, 180, 204)
GOLD = (255, 207, 88)
COLORS = ((83, 193, 241), (240, 151, 220))
RED = (243, 105, 113)
GREEN = (107, 219, 157)
ARROWS = {pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0)}
WASD = {pygame.K_w: (0, -1), pygame.K_s: (0, 1), pygame.K_a: (-1, 0), pygame.K_d: (1, 0)}


class Application:
    def __init__(self, prototype='01', mode='solo', progress_path=None):
        pygame.display.init()
        pygame.font.init()
        pygame.key.set_repeat()
        self.screen = pygame.display.set_mode((960, 780), pygame.RESIZABLE)
        pygame.display.set_caption('Dungeon Escape')
        self.font = pygame.font.Font(None, 25)
        self.title_font = pygame.font.Font(None, 42)
        self.number_font = pygame.font.Font(None, 64)
        self.icon = self.make_icon()
        pygame.display.set_icon(self.icon)
        self.clock = pygame.time.Clock()
        self.page = 'home'
        self.mode = mode
        self.selected = int(prototype) - 1
        self.home_selected = 0
        self.paused = False
        self.cooldowns = [0.0, 0.0]
        self.buttons = []
        self.progress_path = Path(progress_path) if progress_path is not None else Path(__file__).resolve().parents[2] / '.cache/dungeon_escape/progress.json'
        self.completed = {'solo': [], 'coop': []}
        self.scores = clean_scores({})
        self.profile = 'Гравець'
        self.editing_name = False
        self.notice = ''
        self.win_recorded = False
        self.legacy_progress = None
        try:
            saved = json.loads(self.progress_path.read_text(encoding='utf-8'))
            if saved.get('campaign_version') != 2:
                self.legacy_progress = saved
                saved = {'profile': saved.get('profile', 'Гравець')}
            else:
                self.legacy_progress = saved.get('legacy_progress')
            self.scores = clean_scores(saved.get('scores', {}))
            name = saved.get('profile', 'Гравець')
            self.profile = name[:20] if isinstance(name, str) and name.strip() else 'Гравець'
            for key in self.completed:
                values = saved.get(key, [])
                if isinstance(values, list):
                    self.completed[key] = [n for n in values if type(n) is int and 1 <= n <= 9]
        except (OSError, ValueError, AttributeError):
            pass
        self.game = Session(self.stages[self.selected])

    @property
    def stages(self):
        return COOP_STAGES if self.mode == 'coop' else SOLO_STAGES

    @staticmethod
    def make_icon():
        icon = pygame.Surface((96, 96), pygame.SRCALPHA)
        pygame.draw.rect(icon, PANEL, (0, 0, 96, 96), border_radius=20)
        pygame.draw.rect(icon, WALL, (17, 12, 62, 73), border_radius=8)
        pygame.draw.rect(icon, BG, (28, 25, 40, 60), border_radius=12)
        pygame.draw.circle(icon, GOLD, (43, 49), 10, width=4)
        pygame.draw.line(icon, GOLD, (51, 54), (71, 71), 5)
        pygame.draw.line(icon, GOLD, (64, 64), (59, 70), 5)
        return icon

    def text(self, value, pos, color=TEXT, font=None, center=False):
        surface = (font or self.font).render(value, True, color)
        rect = surface.get_rect(center=pos) if center else surface.get_rect(topleft=pos)
        self.screen.blit(surface, rect)

    def button(self, rect, title, action, selected=False):
        rect = pygame.Rect(rect)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, WALL if hover or selected else PANEL, rect, border_radius=12)
        if hover or selected:
            pygame.draw.rect(self.screen, GOLD, rect, width=2, border_radius=12)
        self.text(title, rect.center, GOLD if selected else TEXT, center=True)
        self.buttons.append((rect, action))

    def is_unlocked(self, index):
        return 0 <= index < 9 and all(n in self.completed[self.mode] for n in range(1, index + 1))

    def load_level(self, index, *, preview=False):
        if not preview and not self.is_unlocked(index):
            self.notice = 'Спочатку пройдіть попередні рівні.'
            return False
        self.win_recorded = False
        self.notice = ''
        self.selected = index
        self.game = Session(self.stages[index])
        self.paused = False
        self.cooldowns = [0.18, 0.18]
        self.page = 'play'
        return True

    def levels(self, mode=None):
        if mode is not None:
            self.mode = mode
            self.selected = 0
        self.paused = False
        self.page = 'levels'

    def action(self, action):
        if self.editing_name and action != 'name':
            self.profile = self.profile.strip() or self.original_name
            self.editing_name = False
            pygame.key.stop_text_input()
            self.save_progress()
        if action == 'quit':
            self.game.state = State.EXIT
        elif action in ('solo', 'coop'):
            self.levels(action)
        elif action == 'top':
            self.page = 'top'
        elif action == 'rank_prev':
            self.selected = (self.selected - 1) % 9
        elif action == 'rank_next':
            self.selected = (self.selected + 1) % 9
        elif action == 'rank_mode':
            self.mode = 'coop' if self.mode == 'solo' else 'solo'
        elif action == 'name':
            self.original_name = self.profile
            self.profile = ''
            self.editing_name = True
            pygame.key.start_text_input()
        elif action == 'home':
            self.page = 'home'
        elif action == 'levels':
            self.levels()
        elif action == 'retry':
            self.load_level(self.selected)
        elif action == 'resume':
            self.paused = False
        elif action == 'next':
            self.record_win()
            if self.game.state is not State.WON:
                return
            if self.selected < 8:
                self.load_level(self.selected + 1)
            else:
                self.levels()
        elif isinstance(action, int):
            self.load_level(action)
        self.buttons = []

    def save_progress(self):
        try:
            self.progress_path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.progress_path.with_suffix('.tmp')
            temp.write_text(json.dumps({**self.completed, 'scores': self.scores, 'profile': self.profile, 'campaign_version': 2, 'legacy_progress': self.legacy_progress}, ensure_ascii=False), encoding='utf-8')
            temp.replace(self.progress_path)
        except OSError:
            self.game.message = 'Не вдалося зберегти результат на диску.'

    def record_win(self):
        if self.game.state is not State.WON or self.win_recorded:
            return
        self.win_recorded = True
        number = self.selected + 1
        if number not in self.completed[self.mode]:
            self.completed[self.mode].append(number)
        entries = self.scores[self.mode].setdefault(str(number), [])
        entries.append({'name': self.profile.strip() or 'Гравець',
                        'seconds': round(self.game.elapsed, 3), 'moves': self.game.moves})
        entries.sort(key=lambda entry: (entry['seconds'], entry['moves']))
        del entries[10:]
        self.save_progress()

    def input_move(self, key):
        if self.mode == 'coop':
            owner, direction = (0, ARROWS[key]) if key in ARROWS else (1, WASD.get(key))
        else:
            owner, direction = 0, {**ARROWS, **WASD}.get(key)
        if direction is not None:
            self.game.move(owner, direction)
            self.cooldowns[owner] = 0.13
            self.record_win()

    def handle_event(self, event):
        if self.game.state is State.EXIT:
            return
        if event.type == pygame.QUIT:
            self.action('quit')
        elif event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode((max(800, event.w), max(740, event.h)), pygame.RESIZABLE)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, action in self.buttons:
                if rect.collidepoint(event.pos):
                    self.action(action)
                    break
        elif event.type == pygame.TEXTINPUT and self.editing_name:
            self.profile = (self.profile + ''.join(c for c in event.text if c.isprintable()))[:20]
        elif event.type == pygame.KEYDOWN:
            key = event.key
            if self.editing_name:
                if key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self.editing_name = False
                    self.profile = self.original_name if key == pygame.K_ESCAPE else self.profile.strip() or 'Гравець'
                    pygame.key.stop_text_input()
                    self.save_progress()
                elif key == pygame.K_BACKSPACE:
                    self.profile = self.profile[:-1]
                return
            if key == pygame.K_ESCAPE:
                self.action('levels' if self.page == 'top' else 'home' if self.page == 'levels' else 'levels' if self.page == 'play' else 'quit')
            elif self.page == 'home':
                if key in (pygame.K_DOWN, pygame.K_s, pygame.K_UP, pygame.K_w):
                    self.home_selected = (self.home_selected + (1 if key in (pygame.K_DOWN, pygame.K_s) else -1)) % 4
                elif key == pygame.K_RETURN:
                    self.action(('solo', 'coop', 'top', 'quit')[self.home_selected])
            elif self.page in ('levels', 'top'):
                shifts = {pygame.K_LEFT: -1, pygame.K_a: -1, pygame.K_RIGHT: 1, pygame.K_d: 1,
                          pygame.K_UP: -3, pygame.K_w: -3, pygame.K_DOWN: 3, pygame.K_s: 3}
                if key in shifts:
                    self.selected = (self.selected + shifts[key]) % 9
                elif key == pygame.K_RETURN and self.page == 'levels':
                    self.load_level(self.selected)
                elif key == pygame.K_t:
                    self.page = 'levels' if self.page == 'top' else 'top'
                elif key == pygame.K_TAB and self.page == 'top':
                    self.mode = 'coop' if self.mode == 'solo' else 'solo'
            elif key == pygame.K_m:
                self.levels()
            elif key == pygame.K_r:
                self.load_level(self.selected)
            elif key == pygame.K_p and self.game.state is State.PLAYING:
                self.paused = not self.paused
            elif key == pygame.K_RETURN and self.game.state is State.WON:
                self.action('next')
            elif not self.paused and self.game.state is State.PLAYING:
                self.input_move(key)

    def update(self, dt):
        if self.page != 'play' or self.paused or self.game.state is not State.PLAYING:
            return
        pressed = pygame.key.get_pressed()
        mappings = (ARROWS, WASD) if self.mode == 'coop' else ({**ARROWS, **WASD},)
        for owner, mapping in enumerate(mappings):
            self.cooldowns[owner] = max(0, self.cooldowns[owner] - dt)
            if self.cooldowns[owner] == 0:
                for key, direction in mapping.items():
                    if pressed[key]:
                        self.game.move(owner, direction)
                        self.cooldowns[owner] = 0.13
                        break
        self.game.update(dt)
        self.record_win()

    def draw_menu(self):
        width, height = self.screen.get_size()
        cx = width // 2
        self.screen.blit(self.icon, (cx - 48, 30))
        self.text('DUNGEON ESCAPE', (cx, 157), GOLD, self.title_font, True)
        if self.page == 'home':
            self.text('Знайдіть ключі та виберіться з підземелля', (cx, 206), MUTED, center=True)
            self.button((cx - 200, 270, 400, 64), 'Рівні · один гравець', 'solo', self.home_selected == 0)
            self.button((cx - 200, 354, 400, 64), 'Гра на двох', 'coop', self.home_selected == 1)
            self.button((cx - 200, 438, 400, 64), 'Топ рівнів', 'top', self.home_selected == 2)
            self.button((cx - 180, 544, 360, 44), 'Ім’я: ' + self.profile + ('_' if self.editing_name else ''), 'name')
            self.text('Клацніть ім’я, Backspace — стерти, Enter — зберегти', (cx, 612), MUTED, center=True)
        elif self.page == 'top':
            self.draw_top()
        else:
            title = 'ГРА НА ДВОХ' if self.mode == 'coop' else 'ОДИН ГРАВЕЦЬ'
            self.text(title, (cx, 204), COLORS[self.mode == 'coop'], center=True)
            size, gap = 104, 20
            left = cx - (size * 3 + gap * 2) // 2
            for index in range(9):
                rect = pygame.Rect(left + (index % 3) * (size + gap), 246 + (index // 3) * (size + gap), size, size)
                selected = self.selected == index
                unlocked = self.is_unlocked(index)
                self.button(rect, '', index, selected)
                if not unlocked:
                    pygame.draw.rect(self.screen, BG, rect.inflate(-6, -6), border_radius=10)
                self.text(str(index + 1), (rect.centerx, rect.y + 39), GOLD if selected and unlocked else TEXT if unlocked else MUTED, self.number_font, True)
                if not unlocked:
                    self.text('ЗАКРИТО', (rect.centerx, rect.bottom - 19), MUTED, center=True)
                elif index + 1 in self.completed[self.mode]:
                    self.text('ПРОЙДЕНО', (rect.centerx, rect.bottom - 19), GREEN, center=True)
            stage = self.stages[self.selected]
            self.text(f'Рівень {stage.number} · шлях {stage.distance} кроків · дверей {len(stage.doors)}', (cx, 625), MUTED, center=True)
            self.text(self.notice or 'T — топ вибраного рівня', (cx, 662), MUTED, center=True)
            self.button((32, height - 72, 150, 44), 'Назад', 'home')
            self.button((width - 220, height - 72, 188, 44), 'Топ рівня', 'top')
        self.button((cx - 110, height - 72, 220, 44), 'Вихід', 'quit', self.page == 'home' and self.home_selected == 3)

    def draw_top(self):
        width, height = self.screen.get_size()
        cx = width // 2
        mode = 'Гра на двох' if self.mode == 'coop' else 'Один гравець'
        self.text(f'ЛОКАЛЬНИЙ ТОП · {mode}', (cx, 211), COLORS[self.mode == 'coop'], center=True)
        self.text(f'Рівень {self.selected + 1}', (cx, 254), GOLD, self.title_font, True)
        entries = self.scores[self.mode].get(str(self.selected + 1), [])
        self.button((cx - 275, 235, 62, 42), '<', 'rank_prev')
        self.button((cx + 213, 235, 62, 42), '>', 'rank_next')
        self.text('Місце / ім’я', (cx - 280, 300), MUTED)
        self.text('Час', (cx + 80, 300), MUTED)
        self.text('Кроків', (cx + 235, 300), MUTED)
        for rank, entry in enumerate(entries):
            y = 337 + rank * 30
            self.text(f'{rank + 1}.  {entry["name"]}', (cx - 280, y))
            self.text(format_time(entry['seconds']), (cx + 80, y), GOLD)
            self.text(str(entry['moves']), (cx + 235, y), MUTED)
        if not entries:
            self.text('Ще немає результатів. Пройдіть цей рівень!', (cx, 420), MUTED, center=True)
        self.text('Стрілки — рівень · Tab — режим · T — назад', (cx, 670), MUTED, center=True)
        self.button((32, height - 72, 150, 44), 'Назад', 'levels')
        self.button((width - 220, height - 72, 188, 44), 'Змінити режим', 'rank_mode')

    def key_shape(self, center, color, diamond=False):
        x, y = center
        if diamond:
            pygame.draw.polygon(self.screen, color, [(x, y - 8), (x + 7, y), (x, y + 8), (x - 7, y)], 2)
        else:
            pygame.draw.circle(self.screen, color, (x - 3, y - 2), 5, 2)
            pygame.draw.line(self.screen, color, (x, y + 1), (x + 7, y + 8), 3)
            pygame.draw.line(self.screen, color, (x + 4, y + 5), (x + 1, y + 8), 2)

    def draw_game(self):
        width, height = self.screen.get_size()
        game, stage = self.game, self.game.stage
        self.text(f'Рівень {stage.number} / 9 · ' + ('Гра на двох' if self.mode == 'coop' else 'Один гравець'), (24, 17), GOLD, self.title_font)
        self.text(f'Час: {format_time(game.elapsed)}   Кроків: {game.moves}', (width - 330, 26), MUTED)
        for owner in range(len(game.players)):
            status = 'На виході' if game.finished[owner] else f'Ключів: {game.keys[owner]} · вихід: {"так" if game.exit_keys[owner] else "ні"}'
            control = 'стрілки' if owner == 0 and self.mode == 'coop' else 'WASD' if owner == 1 else 'WASD / стрілки'
            self.text(f'{owner + 1}: {control} · {status}', (24 + owner * (width // 2), 64), COLORS[owner])
        cell = min(40, (width - 48) // stage.width, (height - 215) // stage.height)
        ox, oy = (width - stage.width * cell) // 2, 105
        def rect(pos):
            return pygame.Rect(ox + pos[0] * cell + 1, oy + pos[1] * cell + 1, cell - 2, cell - 2)
        for y, row in enumerate(stage.rows):
            for x, tile in enumerate(row):
                pygame.draw.rect(self.screen, WALL if tile == '#' else PANEL, rect((x, y)), border_radius=3)
        for pos in stage.hazards:
            phase = game.elapsed % stage.hazard_period
            color = RED if game.hazard_active() else GOLD if phase > stage.hazard_period - 0.45 else GREEN
            r = rect(pos).inflate(-4, -4)
            pygame.draw.rect(self.screen, color, r, 2)
            pygame.draw.line(self.screen, color, r.topleft, r.bottomright, 2)
            pygame.draw.line(self.screen, color, r.topright, r.bottomleft, 2)
        for owner, pos in stage.switches:
            r = rect(pos).inflate(-4, -4)
            pygame.draw.circle(self.screen, GREEN if game.team_open else COLORS[owner], r.center, max(6, cell // 3), 3)
        if stage.team_gate is not None and not game.team_open:
            r = rect(stage.team_gate).inflate(-2, -2)
            pygame.draw.rect(self.screen, GOLD, r, 3)
            self.text('2', r.center, GOLD, center=True)
        for i, (owner, pos) in enumerate(stage.doors):
            if i not in game.opened:
                r = rect(pos).inflate(-4, -2)
                pygame.draw.rect(self.screen, COLORS[owner], r, border_radius=3)
                pygame.draw.line(self.screen, BG, r.midtop, r.midbottom, 3)
        for i, (owner, pos) in enumerate(stage.door_keys):
            if i not in game.collected:
                self.key_shape(rect(pos).center, COLORS[owner])
        for owner, pos in enumerate(stage.exit_keys):
            if not game.exit_keys[owner]:
                self.key_shape(rect(pos).center, COLORS[owner], True)
        for owner, pos in enumerate(stage.exits):
            r = rect(pos).inflate(-4, -4)
            pygame.draw.rect(self.screen, GREEN if game.finished[owner] else COLORS[owner], r, 3)
            self.text(str(owner + 1), r.center, COLORS[owner], center=True)
        for pos in game.enemies:
            pygame.draw.rect(self.screen, RED, rect(pos).inflate(-6, -6), border_radius=4)
        for owner, pos in enumerate(game.players):
            if not game.finished[owner]:
                center = rect(pos).center
                if len(game.players) == 2 and game.players[0] == game.players[1]:
                    center = (center[0] + (-cell // 6 if owner == 0 else cell // 6), center[1])
                pygame.draw.circle(self.screen, COLORS[owner], center, max(6, cell // 3))
                self.text(str(owner + 1), center, BG, center=True)
        self.text(game.message, (24, height - 92))
        self.text('R — спочатку · P — пауза · M — рівні · Esc — назад', (24, height - 57), MUTED)
        self.text('Пастки: червона — небезпека · зелена — прохід · жовта — попередження', (24, height - 27), MUTED, pygame.font.Font(None, 21))
        if self.paused or game.state in (State.WON, State.LOST):
            shade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            shade.fill((8, 13, 25, 232))
            self.screen.blit(shade, (0, 0))
            cx, cy = width // 2, height // 2
            heading = 'ПАУЗА' if self.paused else 'РІВЕНЬ ПРОЙДЕНО!' if game.state is State.WON else 'ПОРАЗКА'
            self.text(heading, (cx, cy - 110), GOLD, self.title_font, True)
            if game.state is State.LOST:
                self.text(game.message, (cx, cy - 158), MUTED, center=True)
            if not self.paused:
                self.text(f'Час: {format_time(game.elapsed)} · Кроків: {game.moves}', (cx, cy - 65), MUTED, center=True)
            action = 'resume' if self.paused else 'next' if game.state is State.WON else 'retry'
            label = 'Продовжити' if self.paused else ('Наступний рівень' if self.selected < 8 else 'До вибору рівнів') if game.state is State.WON else 'Спробувати ще раз'
            self.button((cx - 200, cy - 20, 400, 56), label, action)
            self.button((cx - 200, cy + 54, 400, 56), 'Вибір рівня', 'levels')

    def draw(self):
        self.buttons = []
        self.screen.fill(BG)
        if self.page == 'play':
            self.draw_game()
        else:
            self.draw_menu()
        pygame.display.flip()

    def run(self, smoke_test=False, screenshot=None):
        if smoke_test:
            self.load_level(self.selected, preview=True)
        frames = 0
        while self.game.state is not State.EXIT:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            if self.game.state is State.EXIT:
                break
            self.draw()
            frames += 1
            if smoke_test and frames >= 8:
                if screenshot is not None:
                    screenshot.parent.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(self.screen, str(screenshot))
                self.action('quit')
        if smoke_test:
            print(f'Перевірку пройдено: {self.mode}, рівень {self.selected + 1}, кадрів {frames}')
        return 0


def main(default_prototype=None):
    parser = argparse.ArgumentParser(description='Dungeon Escape')
    parser.add_argument('--prototype', choices=[f'{i:02}' for i in range(1, 10)], default=default_prototype or '01')
    parser.add_argument('--mode', choices=('solo', 'coop'), default='solo')
    parser.add_argument('--smoke-test', action='store_true')
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    try:
        return Application(args.prototype, args.mode).run(args.smoke_test, args.screenshot)
    finally:
        pygame.quit()
