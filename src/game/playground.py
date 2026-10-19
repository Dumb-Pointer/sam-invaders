"""A safe, clickable sandbox for trying every weapon and collectible."""

import pygame

from game import (Game, NuclearBomb, WIDTH, HEIGHT,
                  ROBOT_COLUMNS, ROBOT_ROWS, draw)
from game.audio import Audio

ACTIONS = [('missile', '1  Missile'), ('rapid', '2  Rapid fire'),
           ('shield', '3  Shield repair'), ('lollipop', '4  Lollipop'),
           ('laser', '5  Laser'), ('buddies', '6  Rocket buddies'),
           ('drone', '7  Crazy drone'), ('bomb', '8  Nuclear bomb'),
           ('remove_shield', '9  Remove shield'),
           ('invincible', 'I  Invincibility'),
           ('singer', 'O  Singing old man'),
           ('reset', '0  Reset playground')]


class Playground(Game):
    def __init__(self) -> None:
        super().__init__(level=3, progression_enabled=False)
        for player in self.players:
            player.shield = 0
        self.bomb_timer = float('inf')
        self.level_banner = 0
        self.target_timer = 0.0
        self.selected_player = 0
        self.weapon = ''
        self.description = 'Click a button to try its effect.'
        self.reset_targets()

    def reset_targets(self) -> None:
        self.robots = [(c, r) for r in range(ROBOT_ROWS) for c in range(ROBOT_COLUMNS - 1)]
        self.fleet_x, self.fleet_y = 206.0, 120.0
        self.target_timer = 2.8

    def move_fleet(self, dt: float) -> None:
        pass  # Stationary targets make each effect easy to see.

    def trigger(self, action: str) -> None:
        index = self.selected_player
        player = self.players[index]
        if action == 'reset':
            self.__init__()
            return
        if not player.alive:
            player.alive = True
            player.lives = 3
            player.shield = 0
            player.contact_cooldown = 0
            self.lost = False
        if action == 'singer':
            self.summon_singer()
            self.description = 'Grandpa sings both lines. Press O to hear him again.'
            return
        if action.startswith('boss_'):
            self.level = int(action[-1])
            self.weapon = ''
            self.goodies.clear()
            self.start_boss()
            self.description = f'Boss {self.level}: {self.boss_max_health} HP. Real attacks and damage!'
            return
        if action in ('shields_3', 'shields_4'):
            player.max_shield = int(action[-1])
            player.shield = player.max_shield
            player.shield_flash = 0.6
            self.description = f'Player {index + 1}: {player.shield} shields. Repair limit updated too.'
            return
        if action in ('shield', 'lollipop'):
            player.collect(action)
            self.sounds.append('pickup')
            self.description = f'Player {index + 1} shield: {player.shield}/{player.max_shield}. Press 9 to remove it.'
            return
        if action == 'remove_shield':
            player.shield = 0
            player.shield_flash = 0
            self.description = f'Player {index + 1} shield removed. Press 3 to add one segment.'
            return
        if self.boss_active:
            if not self.robots:
                self.start_boss()
        else:
            self.reset_targets()
        player.powers.clear()
        player.missiles.clear()
        player.missile_positions.clear()
        player.buddy_bullets.clear()
        player.fireflies.clear()
        player.drone_ready = False
        player.fire_cooldown = player.buddy_cooldown = player.drone_cooldown = 0.0
        player.laser_flash = 0
        player.rocket_x = 480
        self.weapon = ''
        if action == 'bomb':
            self.bombs.append(NuclearBomb(player.rocket_x, 335))
            self.bombs.append(NuclearBomb(100, 335))
            self.sounds.append('bomb')
            self.description = 'Direct hit is fatal, even with full shields!'
        elif action == 'missile':
            self.weapon = action
            self.description = 'One missile at a time. Firing automatically.'
        else:
            player.collect(action)
            self.sounds.append('pickup')
            if action == 'drone':
                player.activate_drone()
            if action in ('rapid', 'laser'):
                self.weapon = action
            self.description = {'rapid': 'Automatic rapid fire for 10 seconds.',
                                'laser': 'Beam clears every robot in its column.',
                                'buddies': 'Two orbiting rockets shoot automatically.',
                                'drone': '48 propellers! Radial fireflies for 6 seconds.',
                                'invincible': '8 seconds of protection, even from nuclear hits!'}[action]

    def step(self, dt: float, controls: list[tuple[int, int, bool]]) -> None:
        self.target_timer -= dt
        if not self.boss_active and (not self.robots or self.target_timer <= 0):
            self.reset_targets()
        controls = list(controls)
        move, shots, held = controls[self.selected_player]
        if self.weapon:
            shots, held = 1, True
        controls[self.selected_player] = (move, shots, held)
        alive_before = [player.alive for player in self.players]
        self.update(dt, controls)
        if any(before and not player.alive for before, player in zip(alive_before, self.players)):
            self.description = 'Rocket destroyed! Click an effect to revive, or 0 to reset.'
        if self.weapon in ("rapid", "laser") and self.weapon not in self.players[self.selected_player].powers:
            self.weapon = ""


def run() -> None:
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    try:
        screen = pygame.display.set_mode((1260, HEIGHT))
        pygame.display.set_caption('Rocket vs Robots - Goodie Playground')
        canvas = pygame.Surface((WIDTH, HEIGHT))
        font, large = pygame.font.Font(None, 26), pygame.font.Font(None, 76)
        small = pygame.font.Font(None, 21)
        clock, game, audio = pygame.time.Clock(), Playground(), Audio()
        buttons = [(action, label, pygame.Rect(980, 175+i*29, 260, 26))
                   for i, (action, label) in enumerate(ACTIONS)]
        players = [pygame.Rect(980+i*135, 90, 125, 38) for i in range(2)]
        shield_buttons = [(count, pygame.Rect(980+i*135, 134, 125, 30))
                          for i, count in enumerate((3, 4))]
        boss_buttons = [(level, pygame.Rect(1035+(level-1)*41, 538, 37, 29)) for level in range(1, 6)]
        key_actions = {pygame.K_1: 'missile', pygame.K_2: 'rapid', pygame.K_3: 'shield',
                       pygame.K_4: 'lollipop', pygame.K_5: 'laser', pygame.K_6: 'buddies',
                       pygame.K_7: 'drone', pygame.K_8: 'bomb', pygame.K_9: 'remove_shield', pygame.K_0: 'reset', pygame.K_i: 'invincible', pygame.K_o: 'singer'}
        running = True
        paused = False
        while running:
            dt = min(clock.tick(60)/1000, .05)
            shots = [0, 0]
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        game.trigger("reset")
                    elif event.key == pygame.K_m:
                        audio.toggle()
                    elif event.key == pygame.K_p:
                        paused = not paused
                    elif event.key in key_actions:
                        game.trigger(key_actions[event.key])
                    elif event.key in (pygame.K_UP, pygame.K_SPACE):
                        shots[0] += 1
                    elif event.key == pygame.K_x:
                        shots[1] += 1
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, rect in enumerate(players):
                        if rect.collidepoint(event.pos):
                            game.selected_player = i
                            game.weapon = ''
                    for action, _, rect in buttons:
                        if rect.collidepoint(event.pos):
                            game.trigger(action)
                    for level, rect in boss_buttons:
                        if rect.collidepoint(event.pos):
                            game.trigger(f'boss_{level}')
                    for count, rect in shield_buttons:
                        if rect.collidepoint(event.pos):
                            game.trigger(f'shields_{count}')
            keys = pygame.key.get_pressed()
            controls = [(int(keys[pygame.K_RIGHT])-int(keys[pygame.K_LEFT]), shots[0], bool(keys[pygame.K_UP] or keys[pygame.K_SPACE])),
                        (int(keys[pygame.K_c])-int(keys[pygame.K_z]), shots[1], bool(keys[pygame.K_x]))]
            if not paused:
                game.step(dt, controls)
            for sound in game.sounds:
                audio.play(sound)
            game.sounds.clear()
            draw(canvas, game, font, large)
            pygame.draw.rect(canvas, (10, 16, 34), (0, 0, 750, 45))
            canvas.blit(font.render('BOSS TEST  |  Real attacks and damage' if game.boss_active else 'GOODIE PLAYGROUND  |  Real damage  |  Targets respawn', True, (255, 225, 125)), (24, 20))
            # Cover the normal victory message when the final target is destroyed.
            if not game.robots and not game.boss_active:
                pygame.draw.rect(canvas, (10, 16, 34), (0, 230, WIDTH, 150))
            screen.fill((24, 32, 52))
            screen.blit(canvas, (0, 0))
            screen.blit(font.render('PLAYGROUND', True, (245, 235, 175)), (980, 24))
            label = small.render('P: RESUME' if paused else 'P: PAUSE', True, (240, 245, 255))
            screen.blit(label, (1155, 28))
            screen.blit(small.render('Click a button or press 1-9.', True, (180, 200, 225)), (980, 55))
            for i, rect in enumerate(players):
                color = game.players[i].color
                pygame.draw.rect(screen, color if i == game.selected_player else (50, 65, 85), rect, border_radius=6)
                screen.blit(font.render(f'Player {i+1}', True, (10, 20, 35) if i == game.selected_player else (230, 240, 250)), (rect.x+20, rect.y+10))
            for action, label, rect in buttons:
                pygame.draw.rect(screen, (65, 85, 110) if game.weapon == action else (40, 55, 80), rect, border_radius=6)
                screen.blit(font.render(label, True, (230, 240, 250)), (rect.x+12, rect.y+9))
            for count, rect in shield_buttons:
                selected = game.players[game.selected_player].max_shield == count
                pygame.draw.rect(screen, (70, 110, 145) if selected else (40, 55, 80), rect, border_radius=6)
                label = small.render(f'{count} Shields', True, (230, 240, 250))
                screen.blit(label, label.get_rect(center=rect.center))
            screen.blit(small.render('Boss:', True, (255, 180, 160)), (980, 545))
            for level, rect in boss_buttons:
                selected = game.boss_active and game.level == level
                pygame.draw.rect(screen, (170, 65, 85) if selected else (60, 45, 65), rect, border_radius=5)
                label = small.render(str(level), True, (255, 225, 220))
                screen.blit(label, label.get_rect(center=rect.center))
            # Wrap short explanations in the sidebar.
            words, line, yy = game.description.split(), '', 580
            for word in words + ['']:
                if small.size(line+' '+word)[0] > 260 or not word:
                    screen.blit(small.render(line, True, (200, 220, 190)), (980, yy))
                    yy += 19
                    line = word
                else:
                    line = (line+' '+word).strip()
            pygame.display.flip()
    finally:
        pygame.quit()
