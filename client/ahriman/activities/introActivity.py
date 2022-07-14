import time
from os import path

import pyglet
from pyglet.gl import *

from ahriman import constants
from . import Activity
from .customGUIs import Themes
from .loginActivity import LoginActivity


class IntroActivity(Activity):
    def __init__(self, window):
        super().__init__(window)

        self.image = None
        self.background = None
        self.fade_in = None
        self.appear_time = None

        self.current_screen = 0
        self.ended = False
        Themes.load()
        self.load_screen()

    def load_screen(self):
        if self.current_screen < len(constants.INTRO_SCREENS):
            self.image = pyglet.image.load(
                path.join(constants.RESOURCE_PATH, constants.INTRO_SCREENS[self.current_screen]))
            self.background = pyglet.sprite.Sprite(self.image, usage='static')
            self.background.opacity = 0
            self.fade_in = True
            self.update_bg()
            self.current_screen += 1
        else:
            self.end()

    def update(self, dt, bg=False):
        if self.fade_in:
            new_opacity = self.background.opacity + dt * 255 * constants.INTRO_SCREEN_SPEED
            if new_opacity > 255:
                new_opacity = 255
                self.fade_in = False
                self.appear_time = time.time()
            self.background.opacity = new_opacity

        elif time.time() - self.appear_time > constants.INTRO_SCREEN_HOLD:
            new_opacity = self.background.opacity - dt * 255 * constants.INTRO_SCREEN_SPEED
            if new_opacity < 0:
                new_opacity = 0
                self.load_screen()
            self.background.opacity = new_opacity

    def draw(self):
        self.window.draw_2D()
        self.background.draw()

    def update_bg(self):
        h_scale = self.window.height / self.image.height
        v_scale = self.window.width / self.image.width
        if h_scale > v_scale:
            self.background.scale = h_scale
            self.background.position = (-(self.image.width * h_scale - self.window.width) / 2, 0)
        else:
            self.background.scale = v_scale
            self.background.position = (0, -(self.image.height * v_scale - self.window.height) / 2)

    def delete(self):
        pass

    def on_resize(self, width, height):
        self.update_bg()

    def on_key_press(self, KEY, _MOD):
        self.end()

    def on_mouse_release(self, x, y, button, modifiers):
        self.end()

    def end(self):
        if not self.ended:
            self.ended = True
            self.window.change_activity(LoginActivity(self.window), fade_out=True, fade_in=True)
