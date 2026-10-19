import unittest

import pygame

from game import BOSS_ROBOT, BossBolt, Game, NuclearBomb
from game.playground import Playground

IDLE = [(0, 0, False), (0, 0, False)]


def land_missile(game, target):
    rect = game.robot_rect(target)
    player = game.players[0]
    player.missiles = [pygame.Rect(rect.centerx, rect.centery, 10, 28)]
    player.missile_positions = [float(rect.centery)]
    game.update(0, IDLE)


class BossTests(unittest.TestCase):
    def test_each_army_leads_to_a_scaling_boss_then_next_level(self):
        for level, health in enumerate((40, 72, 108, 144, 180), 1):
            with self.subTest(level=level):
                game = Game(level=level, robots=[(0, 0)])
                land_missile(game, (0, 0))
                self.assertTrue(game.boss_active)
                self.assertEqual(game.level, level)
                self.assertEqual(game.boss_health, health)
                game.boss_health = 1
                land_missile(game, BOSS_ROBOT)
                self.assertEqual(game.level, min(level + 1, 5))
                self.assertEqual(bool(game.robots), level < 5)

    def test_laser_damages_boss_instead_of_erasing_it(self):
        game = Game(level=3)
        game.start_boss()
        player = game.players[0]
        player.rocket_x = game.robot_rect(BOSS_ROBOT).centerx
        player.collect('laser')
        game.update(0, [(0, 1, False), (0, 0, False)])
        self.assertEqual(game.boss_health, game.boss_max_health - 3)
        self.assertEqual(game.robots, [BOSS_ROBOT])

    def test_attacks_scale_and_nuclear_bombs_start_at_level_three(self):
        for level in range(1, 6):
            with self.subTest(level=level):
                game = Game(level=level)
                game.start_boss()
                game.boss_attack_timer = game.nuclear_cooldown = 0
                game.update(0, IDLE)
                self.assertEqual(sum(isinstance(b, BossBolt) for b in game.bombs), 1 + level // 2)
                self.assertEqual(any(isinstance(b, NuclearBomb) for b in game.bombs), level >= 3)

    def test_playground_keeps_boss_when_trying_weapons(self):
        game = Playground()
        game.trigger('boss_4')
        game.trigger('laser')
        game.step(0, IDLE)
        self.assertTrue(game.boss_active)
        self.assertEqual(game.boss_health, 141)
        game.target_timer = 0
        game.step(0, IDLE)
        self.assertEqual(game.robots, [BOSS_ROBOT])
        game.trigger('reset')
        self.assertFalse(game.boss_active)
        self.assertEqual(len(game.robots), 36)


if __name__ == '__main__':
    unittest.main()
