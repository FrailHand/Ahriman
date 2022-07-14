import base64
import os
from os import path

import pyglet
from pyglet.gl import *
from pyglet.window import key
from pyglet_gui.buttons import Checkbox
from pyglet_gui.constants import ANCHOR_RIGHT
from pyglet_gui.containers import Spacer, GridContainer
from pyglet_gui.gui import *
from pyglet_gui.text_input import TextInput

from ahriman import constants
from ahriman import logger
from ahriman import strings
from . import Activity
from .customGUIs import FixOneTimeButton, PasswordInput, Themes
from .homeActivity import HomeActivity
from .popupActivity import PopupActivity


class LoginActivity(Activity):
    save_file = path.join(constants.LOCAL_PATH, constants.LOGIN_SAVE_FILE)

    @staticmethod
    def logout():
        if os.path.exists(LoginActivity.save_file):
            os.remove(LoginActivity.save_file)

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

        self.title = SectionHeader(strings.LOGIN_STRING, align=HALIGN_CENTER)

        self.login_button = FixOneTimeButton(label=strings.LOGIN_STRING,
                                             on_release=self.login_click, fixed_width=150)
        self.remember_check = Checkbox(strings.REMEMBER_CHECK)
        login_container = HorizontalContainer([self.login_button, self.remember_check])

        user_title = Label(strings.USERID_TITLE)
        self.userID_field = TextInput()

        password_title = Label(strings.PASSWORD_TITLE)
        self.password_field = PasswordInput()
        login_form = GridContainer(
            [[user_title, self.userID_field], [password_title, self.password_field]],
            anchor=ANCHOR_RIGHT)

        self.info_text = Label(color=[255, 0, 0, 255], italic=True)

        self.exitButton = FixOneTimeButton(label=strings.QUIT_BUTTON_LABEL,
                                           on_release=self.exit_click)

        content.add(self.title)
        content.add(login_form)
        content.add(self.info_text)
        content.add(Spacer(min_height=10))
        content.add(login_container)
        content.add(self.exitButton)

        self.man.set_next_focus(direction=1)

        if path.exists(LoginActivity.save_file):
            with open(LoginActivity.save_file) as file:
                raw = file.read()

            try:
                decoded = base64.b64decode(raw).decode()
                segmented = decoded.split('\n')
                user = segmented[0]
                code = segmented[1]

                self.userID_field.set_text(user)
                self.remember_check.change_state()
                self.man.set_next_focus(direction=1)

                self.password_field.set_text(code)
                self.login_click(True)

            except Exception:
                LoginActivity.logout()

        self.timer = 0

    def login_click(self, is_clicked):
        self.login_button.deactivate()

        self.password = self.password_field.get_password()
        self.userID = self.userID_field.get_text()
        self.remember = self.remember_check.is_pressed

        if not self.remember and path.exists(LoginActivity.save_file):
            LoginActivity.logout()

        if self.password == '' or self.userID == '':
            self.window.fire_event((constants.Event.AUTH_EVENT, constants.AuthEvent.REFUSED))
            return

        logger.info('authenticating')
        self.window.gameClient.authenticate(self.userID, self.password, self.remember)

    def exit_click(self, is_pressed):
        self.window.force_activity(
            PopupActivity(self.window, self, strings.QUIT_POPUP_MESSAGE, self.window.close,
                          no_option=True))

    def on_resize(self, width, height):
        self.update_bg()

    def event_handler(self, event):
        if event[0] == constants.Event.AUTH_EVENT:
            if event[1] == constants.AuthEvent.ERROR:
                self.window.fire_event(
                    (constants.Event.WINDOW_EVENT, constants.WindowEvent.ERROR, strings.SERVER_DOWN_POPUP),
                    priority=True)

            elif event[1] == constants.AuthEvent.SUCCESS:
                if self.remember and event[2] != "":
                    with open(LoginActivity.save_file, 'wb') as file:
                        info_string = '\n'.join((self.userID, event[2]))
                        encoded = base64.b64encode(info_string.encode())
                        file.write(encoded)

                self.window.change_activity(HomeActivity(self.window), fade_out=True, fade_in=True)

            elif event[1] == constants.AuthEvent.REFUSED:
                self.password_field.set_text('')
                self.info_text.set_text(strings.INVALID_CREDENTIALS)
                self.login_button.activate()

        else:
            super().event_handler(event)

    def on_key_press(self, KEY, _MOD):
        if KEY == key.ENTER or KEY == key.NUM_ENTER:
            if self.login_button.active:
                self.login_click(False)
        else:
            super().on_key_press(KEY, _MOD)

    def delete(self):
        self.man.delete()

    def draw(self):
        self.background.draw()
        self.batch.draw()

    def update_bg(self):
        h_scale = self.window.height / self.image.height
        v_scale = self.window.width / self.image.width
        if h_scale > v_scale:
            self.background.scale = h_scale
            self.background.position = (-(self.image.width * h_scale - self.window.width) / 2, 0)
        else:
            self.background.scale = v_scale
            self.background.position = (0, -(self.image.height * v_scale - self.window.height) / 2)
