"""Small synthesized arcade effects, with no external audio assets."""

import math
import random
from array import array
from pathlib import Path

import pygame


class Audio:
    def __init__(self) -> None:
        self.muted = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        if not pygame.mixer.get_init():
            return
        rate, _, channels = pygame.mixer.get_init()
        rng = random.Random(17)
        effects = {
            "boss": (0.9, 180, 60, 0.25),
            "drone": (0.65, 440, 880, 0.04),
            "shoot": (0.16, 1200, 180, 0.05),
            "pickup": (0.35, 550, 1400, 0.0),
            "laser": (0.3, 1600, 90, 0.2),
            "bomb": (0.22, 500, 120, 0.1),
            "nuclear": (0.7, 100, 25, 0.85),
            "explosion": (0.32, 160, 35, 0.8),
            "shield": (0.28, 700, 160, 0.2),
            "break": (0.55, 420, 45, 0.65),
            "lose": (0.85, 240, 35, 0.55),
            "win": (0.8, 440, 880, 0.0),
            "step": (0.08, 110, 65, 0.05),
        }
        for name, (duration, start, end, noise) in effects.items():
            samples = array("h")
            phase = 0.0
            count = int(rate * duration)
            for i in range(count):
                progress = i / count
                frequency = start + (end - start) * progress
                if name == "win":
                    frequency = (523, 659, 784, 1047)[min(3, int(progress * 4))]
                if name == "drone":
                    # Original bright pop arpeggio with a ridiculous robot warble.
                    notes = (523, 659, 784, 988, 880, 784, 659, 1047)
                    frequency = notes[min(7, int(progress * 8))] * (1 + 0.08 * math.sin(progress * 95))
                phase += math.tau * frequency / rate
                envelope = min(1, i / (rate * 0.005)) * (1 - progress) ** 1.5
                value = ((1 - noise) * math.sin(phase) + noise * rng.uniform(-1, 1))
                sample = round(value * envelope * 10000)
                samples.extend([sample] * channels)
            self.sounds[name] = pygame.mixer.Sound(buffer=samples.tobytes())

        song = Path(__file__).with_name("assets") / "old_man_song.wav"
        if song.exists():
            self.sounds["old_man"] = pygame.mixer.Sound(str(song))

    def play(self, name: str) -> None:
        if not self.muted and name in self.sounds:
            self.sounds[name].play()

    def toggle(self) -> None:
        self.muted = not self.muted
        if self.muted and pygame.mixer.get_init():
            pygame.mixer.stop()
