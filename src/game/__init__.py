"""A tiny rocket-versus-robots arcade game."""

import argparse
import copy
import math
import random
from dataclasses import dataclass, field

import pygame

from game.audio import Audio

WIDTH, HEIGHT = 960, 640
ROBOT_COLUMNS, ROBOT_ROWS = 10, 4
ROBOT_WIDTH, ROBOT_HEIGHT = 36, 30
LEVEL_SPEEDS = {1: 80, 2: 110, 3: 110, 4: 220, 5: 440}
DROP_STEP = 28
SHIELD_HEALTH = 3
BOMB_SPEED = 240


@dataclass
class Bomb:
    x: float
    y: float

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - 7, round(self.y) - 10, 14, 20)


@dataclass
class BossBolt(Bomb):
    vx: float = 0.0
    speed: float = 240.0


BOSS_ROBOT = (-1, -1)


def boss_health_for_level(level: int) -> int:
    army = ROBOT_ROWS * (ROBOT_COLUMNS if level == 1 else ROBOT_COLUMNS - 1)
    return army * level


@dataclass
class NuclearBomb(Bomb):
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - 34, round(self.y) - 54, 68, 108)


@dataclass
class NuclearExplosion:
    x: float
    y: float
    age: float = 0.0


POWER_COLORS = {"invincible": (255, 245, 130), "rapid": (255, 205, 70), "shield": (80, 210, 255), "lollipop": (255, 140, 210),
                "laser": (240, 100, 255), "buddies": (100, 255, 160), "drone": (230, 255, 80)}
POWER_LABELS = {"invincible": "INVINCIBLE", "rapid": "RAPID", "shield": "SHIELD", "laser": "LASER", "buddies": "BUDDIES", "drone": "CRAZY DRONE"}


@dataclass
class Goodie(Bomb):
    kind: str = "shield"

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - 20, round(self.y) - 16, 40, 32)


@dataclass
class Firefly:
    x: float
    y: float
    vx: float
    vy: float
    life: float = 2.5

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - 5, round(self.y) - 5, 10, 10)


def propeller_positions(center: tuple[int, int]) -> list[tuple[int, int]]:
    # Three rings of sixteen independently spinning rotors: exactly 48.
    cx, cy = center
    return [(round(cx + math.cos(i * math.tau / 16) * radius),
             round(cy + math.sin(i * math.tau / 16) * radius * 0.6))
            for radius in (20, 36, 52) for i in range(16)]


@dataclass
class Player:
    rocket_x: float = WIDTH / 2
    lives: int = 3
    invulnerable: float = 0.0
    shield: int = SHIELD_HEALTH
    max_shield: int = SHIELD_HEALTH
    shield_flash: float = 0.0
    contact_cooldown: float = 0.0
    missiles: list[pygame.Rect] = field(default_factory=list)
    missile_positions: list[float] = field(default_factory=list)
    powers: dict[str, float] = field(default_factory=dict)
    fire_cooldown: float = 0.0
    drone_cooldown: float = 0.0
    drone_ready: bool = False
    fireflies: list[Firefly] = field(default_factory=list)
    buddy_cooldown: float = 0.0
    buddy_bullets: list[Bomb] = field(default_factory=list)
    laser_x: float = 0.0
    laser_flash: float = 0.0
    pickup_text: str = ""
    pickup_timer: float = 0.0
    alive: bool = True
    color: tuple[int, int, int] = (70, 195, 255)

    def buddy_positions(self, elapsed: float) -> list[tuple[int, int]]:
        return [(round(self.rocket_x + math.cos(elapsed * 2 + phase) * 65),
                 round(HEIGHT - 110 + math.sin(elapsed * 2 + phase) * 26))
                for phase in (0, math.pi)]

    def drone_position(self, elapsed: float) -> tuple[int, int]:
        return (round(self.rocket_x + math.sin(elapsed * 2.7) * 42),
                round(HEIGHT - 200 + math.cos(elapsed * 3.3) * 15))

    def collect(self, kind: str) -> None:
        if kind == "drone":
            self.drone_ready = True
            self.pickup_text = "Drone saved! Activate when in trouble."
        elif kind in ("shield", "lollipop"):
            self.shield = min(self.max_shield, self.shield + 1)
            self.shield_flash = 0.6
            self.pickup_text = "Sweet! Shield repaired!" if kind == "lollipop" else "Shield repaired!"
        else:
            self.powers[kind] = 8.0 if kind == "invincible" else 12.0 if kind in ("buddies", "drone") else 10.0
            self.pickup_text = POWER_LABELS[kind] + " activated!"
        self.pickup_timer = 2.0

    def activate_drone(self) -> bool:
        if not self.alive or not self.drone_ready:
            return False
        self.drone_ready = False
        self.powers["drone"] = 6.0
        self.drone_cooldown = 0.0
        self.pickup_text = "CRAZY DRONE activated!"
        self.pickup_timer = 2.0
        return True



@dataclass
class Game:
    level: int = 1
    progression_enabled: bool = True
    player_count: int = 2
    players: list[Player] = field(default_factory=list)
    level_banner: float = 2.0
    singer_age: float = -1.0
    singer_appeared: bool = False
    boss_active: bool = False
    boss_health: int = 0
    boss_max_health: int = 0
    boss_attack_timer: float = 1.5
    boss_hit_flash: float = 0.0
    elapsed: float = 0.0
    robots: list[tuple[int, int]] = field(default_factory=lambda: [
        (column, row) for row in range(ROBOT_ROWS) for column in range(ROBOT_COLUMNS)
    ])
    fleet_x: float = 120.0
    fleet_y: float = 110.0
    fleet_direction: int = 1
    lost: bool = False
    bombs: list[Bomb] = field(default_factory=list)
    bomb_timer: float = 1.5
    nuclear_cooldown: float = 4.0
    drop_count: int = 0
    drone_dropped: bool = False
    goodies: list[Goodie] = field(default_factory=list)

    sounds: list[str] = field(default_factory=list)
    particles: list[list[float]] = field(default_factory=list)
    nuclear_explosions: list[NuclearExplosion] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.players:
            self.players = [Player(rocket_x=WIDTH / 2 if self.player_count == 1 else WIDTH / 3)]
            if self.player_count == 2:
                self.players.append(Player(rocket_x=WIDTH * 2 / 3, color=(255, 170, 85)))
            if self.level == 5:
                for player in self.players:
                    player.shield = player.max_shield = 4
        if self.level >= 2:
            self.robots = [robot for robot in self.robots if robot[0] < ROBOT_COLUMNS - 1]

    def explode(self, center: tuple[int, int]) -> None:
        for _ in range(24):
            angle, speed = random.uniform(0, math.tau), random.uniform(45, 200)
            self.particles.append([float(center[0]), float(center[1]),
                                   math.cos(angle) * speed, math.sin(angle) * speed,
                                   random.uniform(0.25, 0.65)])

    def nuclear_blast(self, x: float, y: float) -> None:
        self.nuclear_explosions.append(NuclearExplosion(x, y))
        self.sounds.append("nuclear")

    def summon_singer(self) -> None:
        self.singer_age = 0.0
        self.singer_appeared = True
        self.sounds.append("old_man")

    def start_boss(self) -> None:
        self.boss_active = True
        self.boss_health = self.boss_max_health = boss_health_for_level(self.level)
        self.robots = [BOSS_ROBOT]
        self.boss_attack_timer = 1.5
        self.boss_hit_flash = 0
        self.nuclear_cooldown = 5.0
        self.bombs.clear()
        for player in self.players:
            player.missiles.clear()
            player.missile_positions.clear()
            player.buddy_bullets.clear()
            player.fireflies.clear()
        self.level_banner = 2.5
        self.sounds.append("boss")

    def hit_enemy(self, robot: tuple[int, int], damage: int = 1) -> None:
        if robot == BOSS_ROBOT and self.boss_active:
            self.boss_health = max(0, self.boss_health - damage)
            self.boss_hit_flash = 0.1
            if self.boss_health == 0:
                self.robots.remove(robot)
                self.nuclear_blast(*self.robot_rect(robot).center)
        elif robot in self.robots:
            self.robots.remove(robot)

    def boss_attacks(self, dt: float) -> None:
        self.boss_attack_timer -= dt
        rect = self.robot_rect(BOSS_ROBOT)
        if self.boss_attack_timer <= 0:
            count = 1 + self.level // 2
            for i in range(count):
                offset = (i - (count - 1) / 2) * 48
                self.bombs.append(BossBolt(rect.centerx + offset, rect.bottom + 12,
                                           vx=offset, speed=180 + self.level * 25))
            self.sounds.append("bomb")
            self.boss_attack_timer = 1.6 - self.level * 0.18
        if self.level >= 3 and self.nuclear_cooldown == 0:
            self.bombs.append(NuclearBomb(rect.centerx, rect.bottom + 56))
            self.nuclear_cooldown = random.uniform(4.0, 6.0)
            self.sounds.append("bomb")

    def robot_rect(self, robot: tuple[int, int]) -> pygame.Rect:
        if robot == BOSS_ROBOT:
            return pygame.Rect(round(WIDTH / 2 + math.sin(self.elapsed * (0.4 + self.level * 0.12)) * 300) - 80,
                               round(150 + math.sin(self.elapsed * 1.4) * 18), 160, 100)
        column, row = robot
        return pygame.Rect(round(self.fleet_x + column * 64),
                           round(self.fleet_y + row * 54), ROBOT_WIDTH, ROBOT_HEIGHT)

    def move_fleet(self, dt: float) -> None:
        if self.boss_active:
            return
        self.fleet_x += self.fleet_direction * LEVEL_SPEEDS[self.level] * dt
        left = min(self.robot_rect(robot).left for robot in self.robots)
        right = max(self.robot_rect(robot).right for robot in self.robots)
        if self.fleet_direction > 0 and right >= WIDTH - 24:
            self.fleet_x -= right - (WIDTH - 24)
            self.fleet_direction = -1
            self.fleet_y += DROP_STEP
            self.sounds.append("step")
        elif self.fleet_direction < 0 and left <= 24:
            self.fleet_x += 24 - left
            self.fleet_direction = 1
            self.fleet_y += DROP_STEP
            self.sounds.append("step")

    def update(self, dt: float, controls: list[tuple[int, int, bool]],
               activations: tuple[bool, bool] = (False, False)) -> None:
        if self.singer_age >= 0:
            self.singer_age += dt
        for blast in self.nuclear_explosions:
            blast.age += dt
        self.nuclear_explosions = [blast for blast in self.nuclear_explosions if blast.age < 0.9]
        for particle in self.particles:
            particle[0] += particle[2] * dt
            particle[1] += particle[3] * dt
            particle[3] += 160 * dt
            particle[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        self.boss_hit_flash = max(0, self.boss_hit_flash - dt)
        self.level_banner = max(0, self.level_banner - dt)
        if not self.robots or self.lost:
            return
        self.elapsed += dt
        if not self.singer_appeared and self.elapsed >= 6:
            self.summon_singer()
        self.move_fleet(dt)
        for goodie in self.goodies:
            goodie.y += 155 * dt
        for index, (player, (move, fire, held)) in enumerate(zip(self.players, controls)):
            if player.alive:
                if activations[index]:
                    player.activate_drone()
                self.update_player(player, dt, move, fire, held)
        # Resolve missile hits first so a final shot can save the rocket.
        if self.robots and (self.level >= 3 or self.boss_active):
            self.bomb_timer -= dt
            self.nuclear_cooldown = max(0, self.nuclear_cooldown - dt)
            if self.boss_active:
                self.boss_attacks(dt)
            elif self.bomb_timer <= 0:
                # Bottommost robots have a clear path out of the formation.
                front = [robot for robot in self.robots if not any(
                    other[0] == robot[0] and other[1] > robot[1] for other in self.robots)]
                bomber = self.robot_rect(random.choice(front))
                self.drop_count += 1
                if not self.drone_dropped and (self.elapsed >= 20 or len(self.robots) <= 9):
                    self.drone_dropped = True
                    self.goodies.append(Goodie(bomber.centerx, bomber.bottom + 20, "drone"))
                elif self.drop_count % 3 == 0:
                    kind = ("rapid", "invincible", "lollipop", "shield", "laser", "lollipop", "buddies")[(self.drop_count // 3 - 1) % 7]
                    self.goodies.append(Goodie(bomber.centerx, bomber.bottom + 20, kind))
                elif self.nuclear_cooldown == 0:
                    self.bombs.append(NuclearBomb(bomber.centerx, bomber.bottom + 56))
                    self.sounds.append("bomb")
                    self.nuclear_cooldown = random.uniform(4.0, 6.0)
                self.bomb_timer = random.uniform(0.8, 1.4)
            remaining_bombs = []
            for bomb in self.bombs:
                bomb.y += (bomb.speed if isinstance(bomb, BossBolt) else BOMB_SPEED) * dt
                if isinstance(bomb, BossBolt):
                    bomb.x += bomb.vx * dt
                hit_player = next((player for player in self.players if player.alive
                                   and bomb.rect.colliderect(self.player_target(player))), None)
                if hit_player is not None:
                    if isinstance(bomb, NuclearBomb):
                        self.nuclear_blast(bomb.x, bomb.y)
                    else:
                        self.explode((round(bomb.x), round(bomb.y)))
                    self.damage_player(hit_player, fatal=isinstance(bomb, NuclearBomb))
                elif bomb.rect.bottom >= HEIGHT - 40:
                    if isinstance(bomb, NuclearBomb):
                        self.nuclear_blast(bomb.x, HEIGHT - 40)
                    else:
                        self.explode((round(bomb.x), HEIGHT - 40))
                else:
                    remaining_bombs.append(bomb)
            self.bombs = remaining_bombs
        for player in self.players:
            if not player.alive or player.contact_cooldown > 0:
                continue
            hit = next((robot for robot in self.robots
                        if self.robot_rect(robot).colliderect(self.player_target(player))), None)
            if hit is not None:
                self.damage_player(player)
                player.contact_cooldown = 1.5
                self.explode(self.robot_rect(hit).center)
                self.hit_enemy(hit)
        self.lost = not any(player.alive for player in self.players)
        # Reaching the floor must not bypass the rocket's remaining shields.
        if self.robots and min(self.robot_rect(robot).top for robot in self.robots) >= HEIGHT:
            self.fleet_y = 110.0

        if self.lost:
            self.sounds.append("lose")
        elif not self.robots:
            if not self.boss_active and self.progression_enabled:
                self.start_boss()
            else:
                self.sounds.append("win")
                if self.level < 5 and self.progression_enabled:
                    sounds = self.sounds
                    old_players = self.players
                    self.__dict__.update(Game(level=self.level + 1, player_count=self.player_count).__dict__)
                    self.sounds = sounds
                    for player, previous in zip(self.players, old_players):
                        player.lives = previous.lives
                        player.alive = previous.alive
                        if not player.alive:
                            player.shield = 0

    @staticmethod
    def player_target(player: Player) -> pygame.Rect:
        rect = pygame.Rect(round(player.rocket_x) - 24, HEIGHT - 127, 48, 69)
        return rect.inflate(32, 28) if player.shield else rect

    def damage_player(self, player: Player, damage: int = 1, fatal: bool = False) -> None:
        if not player.alive or player.invulnerable > 0 or player.powers.get("invincible", 0) > 0:
            return
        if player.shield and not fatal:
            player.shield = max(0, player.shield - damage)
            player.shield_flash = 0.6
            self.sounds.append("shield" if player.shield else "break")
        else:
            self.explode((round(player.rocket_x), HEIGHT - 92))
            self.sounds.append("explosion")
            remaining = player.lives - 1
            if remaining > 0:
                fresh = Player(rocket_x=player.rocket_x, lives=remaining,
                               shield=player.max_shield, max_shield=player.max_shield,
                               color=player.color, invulnerable=2.0)
                player.__dict__.update(fresh.__dict__)
                player.pickup_text = f"{remaining} lives left! Shield restored."
                player.pickup_timer = 2.0
            else:
                player.lives = player.shield = 0
                player.alive = False

    def update_player(self, player: Player, dt: float, direction: int, shots: int, held_fire: bool) -> None:
        player.invulnerable = max(0, player.invulnerable - dt)
        player.powers = {kind: time - dt for kind, time in player.powers.items() if time > dt}
        player.fire_cooldown = max(0, player.fire_cooldown - dt)
        player.drone_cooldown = max(0, player.drone_cooldown - dt)
        player.buddy_cooldown = max(0, player.buddy_cooldown - dt)
        player.laser_flash = max(0, player.laser_flash - dt)
        player.pickup_timer = max(0, player.pickup_timer - dt)
        player.shield_flash = max(0, player.shield_flash - dt)
        player.contact_cooldown = max(0, player.contact_cooldown - dt)
        player.rocket_x = max(32, min(WIDTH - 32, player.rocket_x + direction * 420 * dt))
        pickup_target = pygame.Rect(round(player.rocket_x) - 44, HEIGHT - 144, 88, 112)
        remaining_goodies = []
        for goodie in self.goodies:
            if goodie.rect.colliderect(pickup_target):
                player.collect(goodie.kind)
                self.sounds.append("pickup")
            elif goodie.rect.top < HEIGHT:
                remaining_goodies.append(goodie)
        self.goodies = remaining_goodies
        double = self.level == 5
        rapid = not double and "rapid" in player.powers
        firing = shots or (rapid and held_fire)
        if firing and player.fire_cooldown == 0:
            if "laser" in player.powers:
                player.laser_x = player.rocket_x
                player.laser_flash = 0.18
                beam = pygame.Rect(round(player.rocket_x) - 8, 0, 16, HEIGHT - 108)
                for robot in self.robots[:]:
                    if beam.colliderect(self.robot_rect(robot)):
                        self.explode(self.robot_rect(robot).center)
                        self.hit_enemy(robot, damage=3)
                self.bombs = [bomb for bomb in self.bombs if not beam.colliderect(bomb.rect)]
                self.sounds.append("laser")
                player.fire_cooldown = 0.18 if rapid else 0.35
            elif not player.missiles or (rapid and len(player.missiles) < 6):
                self.sounds.append("shoot")
                for offset in (-12, 12) if double else (0,):
                    player.missiles.append(pygame.Rect(round(player.rocket_x) + offset - 5, HEIGHT - 108, 10, 28))
                    player.missile_positions.append(float(HEIGHT - 108))
                player.fire_cooldown = 0.16 if rapid else 0.0
        if "buddies" in player.powers and player.buddy_cooldown == 0:
            player.buddy_bullets.extend(Bomb(x, y - 15) for x, y in player.buddy_positions(self.elapsed))
            player.buddy_cooldown = 0.65
            self.sounds.append("shoot")
        if "drone" in player.powers and player.drone_cooldown == 0:
            cx, cy = player.drone_position(self.elapsed)
            for i in range(8):
                angle = i * math.tau / 8 + self.elapsed * 0.7
                player.fireflies.append(Firefly(cx, cy, math.cos(angle) * 260, math.sin(angle) * 260))
            player.drone_cooldown = 1.2
            self.sounds.append("drone")
        remaining_fireflies = []
        for fly in player.fireflies:
            fly.x += fly.vx * dt
            fly.y += fly.vy * dt
            fly.life -= dt
            hit = next((r for r in self.robots if fly.rect.colliderect(self.robot_rect(r))), None)
            if hit is not None:
                self.explode(self.robot_rect(hit).center)
                self.hit_enemy(hit)
                self.sounds.append("explosion")
            elif fly.life > 0 and -10 < fly.x < WIDTH + 10 and -10 < fly.y < HEIGHT + 10:
                remaining_fireflies.append(fly)
        player.fireflies = remaining_fireflies
        remaining_bullets = []
        for bullet in player.buddy_bullets:
            bullet.y -= 620 * dt
            hit = next((r for r in self.robots if bullet.rect.colliderect(self.robot_rect(r))), None)
            if hit is not None:
                self.explode(self.robot_rect(hit).center)
                self.sounds.append("explosion")
                self.hit_enemy(hit)
            elif bullet.rect.bottom > 0:
                remaining_bullets.append(bullet)
        player.buddy_bullets = remaining_bullets
        remaining, positions = [], []
        for missile, y in zip(player.missiles, player.missile_positions):
            y -= 620 * dt
            missile.y = round(y)
            hit = next((robot for robot in self.robots if missile.colliderect(self.robot_rect(robot))), None)
            if hit is not None:
                self.explode(self.robot_rect(hit).center)
                self.sounds.append("explosion")
                self.hit_enemy(hit)
            elif missile.bottom > 0:
                remaining.append(missile)
                positions.append(y)
        player.missiles, player.missile_positions = remaining, positions


def draw(screen: pygame.Surface, game: Game, font: pygame.font.Font, large: pygame.font.Font) -> None:
    screen.fill((10, 16, 34))
    rng = random.Random(42)
    for _ in range(85):
        x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        pygame.draw.circle(screen, (100, 125, 160), (x, y), rng.choice((1, 1, 2)))
    screen.blit(font.render(f"ROCKET vs ROBOTS  |  LEVEL {game.level}", True, (230, 240, 255)), (24, 20))
    screen.blit(font.render("P1: Left/Right + Up/Space   P2: Z/C + X   M: mute   R: restart   Esc: quit", True, (150, 175, 205)), (24, HEIGHT - 32))

    for index, player in enumerate(game.players):
        draw_player(screen, game, player, index, font)

    for bomb in game.bombs:
        if isinstance(bomb, BossBolt):
            rect = bomb.rect
            cx = rect.centerx
            pygame.draw.ellipse(screen, (105, 145, 65), rect)
            for offset in (6, 12):
                pygame.draw.line(screen, (45, 75, 35), (rect.left + 2, rect.top + offset),
                                 (rect.right - 3, rect.top + offset), 2)
            pygame.draw.line(screen, (45, 75, 35), (cx, rect.top + 2), (cx, rect.bottom - 2), 2)
            pygame.draw.rect(screen, (80, 90, 65), (cx - 4, rect.top - 4, 8, 6))
            pygame.draw.lines(screen, (185, 190, 165), False,
                              [(cx - 3, rect.top - 5), (cx + 6, rect.top - 3),
                               (rect.right + 2, rect.centery)], 2)
            pygame.draw.circle(screen, (205, 210, 180), (cx - 6, rect.top - 5), 4, 1)
        else:
            draw_nuclear_bomb(screen, bomb)

    for goodie in game.goodies:
        if goodie.kind == "lollipop":
            cx, cy = goodie.rect.center
            pygame.draw.line(screen, (245, 240, 225), (cx, cy), (cx, cy + 18), 4)
            pygame.draw.circle(screen, (255, 130, 200), (cx, cy - 4), 14)
            spiral = [(round(cx + math.cos(t * 0.13) * t * 0.14),
                       round(cy - 4 + math.sin(t * 0.13) * t * 0.14)) for t in range(85)]
            pygame.draw.lines(screen, (255, 245, 240), False, spiral, 3)
            continue
        color = POWER_COLORS[goodie.kind]
        pygame.draw.rect(screen, (15, 30, 50), goodie.rect, border_radius=7)
        pygame.draw.rect(screen, color, goodie.rect, 3, border_radius=7)
        icon = font.render({"rapid": "F", "shield": "+", "laser": "L", "buddies": "B", "drone": "D", "invincible": "I"}[goodie.kind], True, color)
        screen.blit(icon, icon.get_rect(center=goodie.rect.center))

    screen.blit(font.render(f"BOSS {game.boss_health} HP" if game.boss_active else f"ROBOTS LEFT: {len(game.robots)}", True, (160, 225, 150)), (WIDTH - 200, 24))
    for robot in game.robots:
        if robot == BOSS_ROBOT:
            draw_boss(screen, game, font)
            continue
        rect = game.robot_rect(robot)
        cx, cy = rect.center
        color = [(140, 215, 85), (105, 195, 230), (200, 145, 235), (255, 175, 95)][robot[1] % 4]
        pygame.draw.line(screen, color, (cx, rect.top), (cx, rect.top - 6), 2)
        pygame.draw.circle(screen, (255, 210, 100), (cx, rect.top - 7), 3)
        pygame.draw.rect(screen, color, rect, border_radius=5)
        for dx in (-9, 9):
            pygame.draw.rect(screen, (15, 30, 45), (cx + dx - 3, cy - 7, 6, 7))
            foot_x = cx + dx + (3 if int(game.elapsed * 4) % 2 else -3)
            pygame.draw.line(screen, color, (cx + dx, rect.bottom - 2), (foot_x, rect.bottom + 5), 4)
        pygame.draw.line(screen, (35, 55, 70), (cx - 8, cy + 6), (cx + 8, cy + 6), 2)
    for px, py, _, _, life in game.particles:
        color = (255, min(240, round(100 + life * 200)), 60)
        pygame.draw.circle(screen, color, (round(px), round(py)), max(1, round(life * 7)))
    for blast in game.nuclear_explosions:
        # Local translucent mushroom cloud: no blast hitbox or extra damage.
        cloud = pygame.Surface((180, 150), pygame.SRCALPHA)
        progress = blast.age / 0.9
        alpha = round(210 * (1 - progress))
        spread = round(30 + 42 * min(1, progress * 3))
        rise = round(30 * min(1, progress * 3))
        pygame.draw.ellipse(cloud, (255, 180, 60, alpha), (90-spread, 112-spread//4, spread*2, 26), 4)
        pygame.draw.rect(cloud, (255, 130, 40, alpha), (79, 70-rise, 22, 55+rise), border_radius=8)
        for dx, dy, radius in ((-34, 0, 28), (0, -12, 36), (34, 0, 28)):
            center = (90 + round(dx * spread / 72), 70 - rise + dy)
            pygame.draw.circle(cloud, (255, 130, 40, alpha), center, radius)
            pygame.draw.circle(cloud, (255, 225, 100, alpha), center, radius-9)
        screen.blit(cloud, (round(blast.x)-90, round(blast.y)-125))
    if 0 <= game.singer_age < 5.5:
        draw_singer(screen, game, font)
    if game.level_banner > 0 and game.robots and not game.lost:
        subtitle = {1: "Ready to launch!", 2: "Faster robots!", 3: "Watch out for bombs!", 4: "Double-speed robots!", 5: "Super-speed robots!"}[game.level]
        subtitle = "BOSS INCOMING!" if game.boss_active else subtitle
        label = font.render(f"LEVEL {game.level}  —  {subtitle}", True, (255, 225, 125))
        screen.blit(label, label.get_rect(center=(WIDTH // 2, 370)))
    if game.lost or not game.robots:
        title = "ROCKET DESTROYED" if game.lost else "BOSS DEFEATED!" if game.boss_active else "YOU WIN!"
        message = "Press R to play again."
        overlay = pygame.Surface((WIDTH, 150), pygame.SRCALPHA)
        overlay.fill((10, 16, 34, 220))
        screen.blit(overlay, (0, 230))
        for text, yy, face in [(title, 275, large), (message, 335, font)]:
            label = face.render(text, True, (255, 170, 140) if game.lost else (150, 240, 180))
            screen.blit(label, label.get_rect(center=(WIDTH // 2, yy)))



def draw_singer(screen: pygame.Surface, game: Game, font: pygame.font.Font) -> None:
    x, y = 85, 445 + round(math.sin(game.singer_age * 9) * 4)
    # One little grandpa: silver hair, glasses, moustache, cardigan and cane.
    pygame.draw.line(screen, (125, 95, 70), (x+31, y+4), (x+31, y+66), 4)
    for dx in (-10, 10):
        pygame.draw.line(screen, (65, 65, 90), (x+dx, y+35), (x+dx, y+63), 9)
        pygame.draw.ellipse(screen, (45, 40, 50), (x+dx-9, y+58, 18, 8))
    pygame.draw.rect(screen, (140, 95, 145), (x-22, y-3, 44, 42), border_radius=9)
    pygame.draw.line(screen, (235, 190, 155), (x-18, y+7), (x-37, y-10-round(math.sin(game.singer_age*8)*9)), 7)
    pygame.draw.circle(screen, (220, 220, 215), (x, y-22), 25)
    pygame.draw.circle(screen, (235, 190, 155), (x, y-17), 20)
    pygame.draw.arc(screen, (235, 235, 225), (x-25, y-47, 50, 45), 0, math.pi, 8)
    for dx in (-9, 9):
        pygame.draw.circle(screen, (65, 65, 75), (x+dx, y-20), 8, 2)
        pygame.draw.circle(screen, (40, 40, 50), (x+dx, y-20), 2)
    pygame.draw.line(screen, (65, 65, 75), (x-1,y-20),(x+1,y-20),2)
    pygame.draw.ellipse(screen, (80, 40, 45), (x-5,y-7,10,8))
    pygame.draw.ellipse(screen, (245, 240, 225), (x-12,y-12,24,7))
    phrase = "Gradili lia kilia" if game.singer_age < 2.11 else '"Pecal" в нея скумрия'
    label = font.render(phrase, True, (65, 40, 75))
    bubble = label.get_rect(topleft=(x+45,y-75)).inflate(22,18)
    pygame.draw.rect(screen, (255, 240, 200), bubble, border_radius=12)
    screen.blit(label, label.get_rect(center=bubble.center))
    for i in range(3):
        nx, ny = x-35+i*30, y-65-round((game.singer_age*25+i*15)%40)
        pygame.draw.circle(screen, (255, 220, 115), (nx,ny), 4)
        pygame.draw.line(screen,(255,220,115),(nx+3,ny),(nx+3,ny-12),2)


def draw_boss(screen: pygame.Surface, game: Game, font: pygame.font.Font) -> None:
    rect = game.robot_rect(BOSS_ROBOT)
    cx, cy = rect.center
    color = (255, 245, 220) if game.boss_hit_flash else (175, 70, 95)
    pygame.draw.line(screen, (100, 150, 180), (cx-95, cy-10), (cx+95, cy-10), 16)
    pygame.draw.rect(screen, color, rect, border_radius=20)
    for dx in (-43, 43):
        pygame.draw.circle(screen, (255, 210, 80), (cx+dx, cy-12), 19)
        pygame.draw.circle(screen, (35, 25, 50), (cx+dx, cy-12), 9)
        pygame.draw.rect(screen, (85, 95, 120), (cx+dx-10, rect.bottom-12, 20, 30), border_radius=4)
    pygame.draw.rect(screen, (30, 25, 45), (cx-40, cy+20, 80, 13), border_radius=4)
    for i in range(game.level):
        pygame.draw.circle(screen, (255, 150, 60), (cx-24+i*12, rect.top+8), 4)
    bar = pygame.Rect(cx-110, rect.top-40, 220, 13)
    pygame.draw.rect(screen, (60, 45, 65), bar, border_radius=5)
    if game.boss_max_health:
        pygame.draw.rect(screen, (255, 90, 110), (bar.x, bar.y, round(bar.width*game.boss_health/game.boss_max_health), bar.height), border_radius=5)
    label = font.render(f"BOSS {game.level}: {game.boss_health}/{game.boss_max_health}", True, (255, 210, 210))
    screen.blit(label, label.get_rect(center=(cx, bar.y-14)))


def draw_nuclear_bomb(screen: pygame.Surface, bomb: Bomb) -> None:
    sprite = pygame.Surface((34, 54), pygame.SRCALPHA)
    rect = sprite.get_rect()
    cx, cy = rect.center
    pygame.draw.polygon(sprite, (210, 135, 40), [(cx - 15, rect.top), (cx + 15, rect.top),
                        (cx + 9, rect.top + 18), (cx - 9, rect.top + 18)])
    pygame.draw.ellipse(sprite, (245, 190, 50), (cx - 17, rect.top + 9, 34, 45))
    pygame.draw.ellipse(sprite, (255, 230, 125), (cx - 12, rect.top + 15, 7, 26))
    pygame.draw.circle(sprite, (40, 40, 45), (cx, cy + 4), 11)
    pygame.draw.circle(sprite, (255, 215, 50), (cx, cy + 4), 3)
    for angle in (0, math.tau / 3, math.tau * 2 / 3):
        points = [(cx + round(math.cos(angle + offset) * radius),
                   cy + 4 + round(math.sin(angle + offset) * radius))
                  for offset, radius in ((-0.35, 5), (-0.35, 10), (0.35, 10), (0.35, 5))]
        pygame.draw.polygon(sprite, (255, 215, 50), points)
    screen.blit(pygame.transform.scale(sprite, bomb.rect.size), bomb.rect)

def draw_player(screen: pygame.Surface, game: Game, player: Player, index: int, font: pygame.font.Font) -> None:
    hud_x = 24 + index * 460
    hud_font = pygame.font.Font(None, 20)
    status = f"P{index + 1}  LIVES {player.lives}  SHIELD {player.shield}/{player.max_shield}" if player.alive else f"P{index + 1}  OUT OF LIVES"
    screen.blit(font.render(status, True, player.color), (hud_x, 53))
    if player.drone_ready:
        key = "Right Shift" if index == 0 else "V"
        screen.blit(hud_font.render(f"DRONE READY: {key}", True, POWER_COLORS["drone"]), (hud_x, 77))
    if game.level == 5:
        screen.blit(hud_font.render("DOUBLE MISSILES: tap shoot", True, (255, 220, 110)), (hud_x, 77))
    for i, (kind, time) in enumerate(player.powers.items(), start=int(player.drone_ready or game.level == 5)):
        screen.blit(hud_font.render(f"{POWER_LABELS[kind]} {math.ceil(time)}s", True, POWER_COLORS[kind]), (hud_x + (i % 2) * 220, 77 + (i // 2) * 17))
    if not player.alive:
        return
    if player.invulnerable > 0 and int(game.elapsed * 10) % 2:
        return
    x, y = round(player.rocket_x), HEIGHT - 92
    if "invincible" in player.powers:
        radius = 52 + round(math.sin(game.elapsed * 8) * 3)
        pygame.draw.circle(screen, (255, 235, 100), (x, y), radius, 3)
        for angle in range(0, 360, 45):
            radians = math.radians(angle) + game.elapsed
            pygame.draw.circle(screen, (255, 255, 210),
                               (x + round(math.cos(radians)*radius), y + round(math.sin(radians)*radius)), 3)
    flame = 22 + round(math.sin(game.elapsed * 35) * 7)
    pygame.draw.polygon(screen, (255, 165, 55), [(x - 11, y + 28), (x, y + 28 + flame), (x + 11, y + 28)])
    pygame.draw.polygon(screen, player.color, [(x - 17, y), (x - 31, y + 34), (x + 31, y + 34), (x + 17, y)])
    pygame.draw.polygon(screen, (220, 235, 250), [(x, y - 35), (x - 17, y + 5), (x - 15, y + 28), (x + 15, y + 28), (x + 17, y + 5)])
    pygame.draw.circle(screen, player.color, (x, y), 9)
    if player.shield or player.shield_flash:
        shield_color = (255, 210, 130) if player.shield_flash else player.color
        # Missing arcs make the shield's remaining strength visible on the ship.
        for segment in range(player.shield):
            start = segment * math.tau / player.max_shield + 0.08
            pygame.draw.arc(screen, shield_color, (x - 45, y - 52, 90, 102),
                            start, start + math.tau / player.max_shield - 0.16, 4)
        if player.shield_flash:
            pygame.draw.ellipse(screen, shield_color, (x - 49, y - 56, 98, 110), 2)
    for missile in player.missiles:
        pygame.draw.rect(screen, (255, 225, 125), missile, border_radius=5)
        pygame.draw.polygon(screen, (255, 115, 60), [(missile.left, missile.bottom), (missile.centerx, missile.bottom + 12), (missile.right, missile.bottom)])

    if "drone" in player.powers:
        center = player.drone_position(game.elapsed)
        cx, cy = center
        for i, (px, py) in enumerate(propeller_positions(center)):
            pygame.draw.line(screen, (70, 105, 110), center, (px, py), 1)
            pygame.draw.circle(screen, (80, 130, 145), (px, py), 5, 1)
            angle = game.elapsed * 35 + i
            dx, dy = round(math.cos(angle) * 5), round(math.sin(angle) * 3)
            pygame.draw.line(screen, (200, 255, 145), (px - dx, py - dy), (px + dx, py + dy), 2)
        pygame.draw.ellipse(screen, (190, 90, 235), (cx - 17, cy - 13, 34, 26))
        pygame.draw.circle(screen, (245, 255, 100), (cx, cy), 7)
        pygame.draw.circle(screen, (30, 30, 55), (cx + 2, cy), 3)
    for fly in player.fireflies:
        fx, fy = round(fly.x), round(fly.y)
        flutter = round(math.sin(game.elapsed * 45 + fly.x) * 4)
        pygame.draw.circle(screen, (55, 90, 40), (fx, fy), 8)
        pygame.draw.ellipse(screen, (140, 235, 200), (fx - 7, fy - 4 - flutter, 6, 5))
        pygame.draw.ellipse(screen, (140, 235, 200), (fx + 1, fy - 4 + flutter, 6, 5))
        pygame.draw.circle(screen, (235, 255, 90), (fx, fy), 3)
    if "buddies" in player.powers:
        for bx, by in player.buddy_positions(game.elapsed):
            pygame.draw.polygon(screen, (100, 255, 160), [(bx, by - 16), (bx - 12, by + 12), (bx + 12, by + 12)])
            pygame.draw.circle(screen, (235, 255, 245), (bx, by + 2), 4)
            pygame.draw.line(screen, (255, 180, 70), (bx, by + 12), (bx, by + 20), 4)
    for bullet in player.buddy_bullets:
        pygame.draw.rect(screen, (100, 255, 160), bullet.rect, border_radius=5)
    if player.laser_flash:
        pygame.draw.line(screen, (160, 60, 220), (round(player.laser_x), HEIGHT - 108), (round(player.laser_x), 0), 22)
        pygame.draw.line(screen, (255, 220, 255), (round(player.laser_x), HEIGHT - 108), (round(player.laser_x), 0), 7)
    if player.pickup_timer:
        label = font.render(player.pickup_text, True, (255, 240, 170))
        screen.blit(label, label.get_rect(center=(round(player.rocket_x), 450 + index * 25)))


def demo_controls(game: Game, player: Player, dt: float) -> tuple[int, int]:
    """Aim ahead of moving robots using their actual speed and edge turns."""
    if game.lost or not game.robots or not player.alive:
        return 0, 0
    targets = []
    for row in sorted({robot[1] for robot in game.robots}, reverse=True):
        future = copy.copy(game)
        future.sounds = []
        flight = max(0, (HEIGHT - 108 - (game.fleet_y + row * 54 + ROBOT_HEIGHT)) / 620)
        steps = max(1, math.ceil(flight * 60))
        for _ in range(steps):
            future.move_fleet(flight / steps)
        for robot in game.robots:
            if robot[1] == row:
                targets.append(future.robot_rect(robot).centerx)
    aim = min(targets, key=lambda x: abs(x - player.rocket_x))
    difference = aim - player.rocket_x
    direction = (1 if difference > 0 else -1) if abs(difference) > max(3, 420 * dt) else 0
    return direction, int(abs(difference) <= 14 and not player.missiles)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rocket vs Robots")
    parser.add_argument("--demo", action="store_true", help="Watch the autopilot play")
    parser.add_argument("--level", type=int, choices=(1, 2, 3, 4, 5), default=1, help="Choose the starting level")
    parser.add_argument("--players", type=int, choices=(1, 2), default=2, help="Number of players")
    parser.add_argument("--playground", action="store_true", help="Test every goodie and weapon")
    parser.add_argument("--boss", action="store_true", help="Start directly at the chosen level's boss")
    parser.add_argument("--paused", action="store_true", help="Wait for Enter or Start fight before playing")
    args = parser.parse_args()
    if args.playground:
        from game.playground import run
        run()
        return
    demo = args.demo
    paused = args.paused
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Rocket vs Robots")
        clock = pygame.time.Clock()
        font, large = pygame.font.Font(None, 26), pygame.font.Font(None, 76)
        game = Game(level=args.level, player_count=args.players)
        if args.boss:
            game.start_boss()
        audio = Audio()
        player_buttons = [(count, pygame.Rect(520 + (count - 1) * 114, 17, 110, 32))
                          for count in (1, 2)]
        running = True
        while running:
            dt = min(clock.tick(60) / 1000, 0.05)
            shots = [0, 0]
            activations = [False, False]
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for count, rect in player_buttons:
                        if rect.collidepoint(event.pos) and count != game.player_count:
                            args.players = count
                            game = Game(level=game.level, player_count=count)
                            if args.boss:
                                game.start_boss()
                            shots = [0, 0]
                            activations = [False, False]
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_RETURN:
                        paused = False
                    elif event.key == pygame.K_p:
                        paused = not paused
                    elif event.key == pygame.K_r:
                        game = Game(level=args.level, player_count=args.players)
                        if args.boss:
                            game.start_boss()
                    elif event.key == pygame.K_d:
                        demo = not demo
                    elif event.key == pygame.K_m:
                        audio.toggle()
                    elif event.key in (pygame.K_UP, pygame.K_SPACE):
                        shots[0] += 1
                    elif event.key == pygame.K_x:
                        shots[1] += 1
                    elif event.key == pygame.K_RSHIFT:
                        activations[0] = True
                    elif event.key == pygame.K_v:
                        activations[1] = True
            keys = pygame.key.get_pressed()
            controls = [(int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT]), shots[0], bool(keys[pygame.K_UP] or keys[pygame.K_SPACE])),
                        (int(keys[pygame.K_c]) - int(keys[pygame.K_z]), shots[1], bool(keys[pygame.K_x]))]
            if demo:
                controls = []
                for player in game.players:
                    direction, fire = demo_controls(game, player, dt)
                    controls.append((direction, fire, bool(fire)))
            if not paused:
                game.update(dt, controls, tuple(activations))
            for sound in game.sounds:
                audio.play(sound)
            game.sounds.clear()
            draw(screen, game, font, large)
            for count, rect in player_buttons:
                selected = count == game.player_count
                pygame.draw.rect(screen, (70, 180, 210) if selected else (40, 55, 80), rect, border_radius=6)
                title = f"{count} Player{'s' if count == 2 else ''}"
                label = font.render(title, True, (10, 20, 35) if selected else (230, 240, 250))
                screen.blit(label, label.get_rect(center=rect.center))
            status = "DEMO: AUTOPILOT PLAYING  |  D: take control" if demo else "D: watch demo"
            label = font.render(status, True, (255, 215, 105))
            screen.blit(label, label.get_rect(center=(WIDTH // 2, HEIGHT - 58)))
            if paused:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((8, 12, 25, 150))
                screen.blit(overlay, (0, 0))
                title = "PAUSED" if game.elapsed > 0 else f"BOSS {game.level} READY?" if game.boss_active else "READY?"
                label = large.render(title, True, (245, 235, 175))
                screen.blit(label, label.get_rect(center=(WIDTH // 2, 285)))
                label = font.render("Press P to resume / start", True, (245, 235, 175))
                screen.blit(label, label.get_rect(center=(WIDTH // 2, 370)))
            label = font.render("P: pause / resume", True, (180, 205, 230))
            screen.blit(label, label.get_rect(bottomright=(WIDTH - 24, HEIGHT - 48)))
            pygame.display.flip()
    finally:
        pygame.quit()
