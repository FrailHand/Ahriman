import math
import time
from os import path

import pyglet
from pyglet.gl import *
from pyglet_gui.containers import Spacer
from pyglet_gui.gui import *

from ahriman import constants
from ahriman import logger
from ahriman import strings
from ahriman.activities import Activity
from ahriman.activities.customGUIs import FixOneTimeButton, FixButton
from ahriman.activities.customGUIs import Themes
from ahriman.activities.loadingActivity import LoadingActivity
from ahriman.activities.popupActivity import PopupActivity


class HomeActivity(Activity):
    def __init__(self, window):
        super().__init__(window)

        self.batch = pyglet.graphics.Batch()
        self.image = pyglet.image.load(
            path.join(constants.RESOURCE_PATH, 'backgrounds', 'menu.png'))
        self.background = pyglet.sprite.Sprite(self.image, usage='static')
        self.update_bg()

        content = VerticalContainer([], align=HALIGN_CENTER)

        self.man = Manager(Frame(content), window=self.window, batch=self.batch,
                           anchor=ANCHOR_CENTER, theme=Themes.menuTheme, is_movable=False)

        self.title = SectionHeader(strings.MAIN_MENU_TITLE, align=HALIGN_CENTER)
        self.playButton = FixButton(label=strings.PLAY_BUTTON_LABEL, on_press=self.play_click)
        self.logout_button = FixOneTimeButton(label=strings.LOGOUT_BUTTON_LABEL,
                                              on_release=self.logout_click)
        self.exitButton = FixOneTimeButton(label=strings.QUIT_BUTTON_LABEL,
                                           on_release=self.exit_click)

        content.add(self.title)
        content.add(Spacer(min_height=20))
        content.add(self.playButton)
        content.add(self.logout_button)
        content.add(self.exitButton)

        self.timer = 0

    def on_resize(self, width, height):
        self.update_bg()

    def event_handler(self, event):
        if event[0] == constants.Event.SEARCH_EVENT:

            if event[1] == constants.SearchEvent.GAME_FOUND:
                self.window.change_activity(LoadingActivity(self.window), fade_in=True,
                                            fade_out=True)

            elif event[1] == constants.SearchEvent.PENDING_FOUND:
                self.window.change_activity(LoadingActivity(self.window, reconnecting=True),
                                            fade_in=True, fade_out=True)

            elif event[1] == constants.SearchEvent.CANCELED:
                logger.confirm('canceled game request')

            elif event[1] == constants.SearchEvent.OUT_OF_ID:
                self.playButton.change_state()
                self.window.force_activity(PopupActivity(self.window, self, strings.NO_ROOMS_POPUP))

            elif event[1] == constants.SearchEvent.ERROR:
                self.playButton.change_state()
                self.window.fire_event(
                    (constants.Event.WINDOW_EVENT, constants.WindowEvent.ERROR, strings.SERVER_DOWN_POPUP),
                    priority=True)

            else:
                super().event_handler(event)

        elif event[0] == constants.Event.GAME_EVENT and event[1] == constants.GameEvent.END_OF_CONNECTION:
            logger.confirm('game session closed')
        else:
            super().event_handler(event)

    def delete(self):
        self.man.delete()

    def draw(self):
        self.background.draw()
        self.batch.draw()

    def update(self, dt, bg=False):
        elapsed = math.floor(time.time() - self.timer)
        self.playButton.label = ''.join(
            (strings.SEARCHING_BUTTON_LABEL, " {0:02}'{1:02}\"")).format((elapsed // 60) % 100,
                                                                         elapsed % 60) if self.playButton.is_pressed else strings.PLAY_BUTTON_LABEL
        self.playButton.reload()
        self.playButton.reset_size()

    def play_click(self, is_on):
        if is_on:
            self.window.gameClient.search_game(constants.DEFAULT_QUEUE)
            self.timer = time.time()
        else:
            self.window.gameClient.cancel_search()

    def exit_click(self, is_pressed):
        self.window.force_activity(
            PopupActivity(self.window, self, strings.QUIT_POPUP_MESSAGE, self.window.close,
                          no_option=True))

    def logout_click(self, is_pressed):
        from .loginActivity import LoginActivity

        def logout():
            self.window.gameClient.quit()
            LoginActivity.logout()
            self.window.change_activity(LoginActivity(self.window), fade_out=True, fade_in=True)

        self.window.force_activity(
            PopupActivity(self.window, self, strings.LOGOUT_POPUP_MESSAGE, logout, no_option=True))

    def update_bg(self):
        h_scale = self.window.height / self.image.height
        v_scale = self.window.width / self.image.width
        if h_scale > v_scale:
            self.background.scale = h_scale
            self.background.position = (-(self.image.width * h_scale - self.window.width) / 2, 0)
        else:
            self.background.scale = v_scale
            self.background.position = (0, -(self.image.height * v_scale - self.window.height) / 2)
