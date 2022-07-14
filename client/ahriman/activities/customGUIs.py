import json
from builtins import FileNotFoundError
from os import path

import pyglet
from pyglet_gui.buttons import Button, OneTimeButton
from pyglet_gui.gui import Frame
from pyglet_gui.text_input import TextInput
from pyglet_gui.theme import Theme

from ahriman import constants
from ahriman import logger


class Themes:
    menuTheme = None
    overLayerTheme = None
    overlayTheme = None

    @staticmethod
    def load():
        try:
            with open(path.join(constants.RESOURCE_PATH, 'themes', 'menu', 'theme.json'),
                      'r') as file:
                Themes.menuTheme = Theme(json.load(file),
                                         resources_path=path.join(constants.RESOURCE_PATH, 'themes',
                                                                  'menu'))
        except FileNotFoundError as e:
            logger.error(e.strerror, e.filename, title='in menu loading')

        try:
            with open(path.join(constants.RESOURCE_PATH, 'themes', 'overlayer', 'theme.json'),
                      'r') as file:
                Themes.overLayerTheme = Theme(json.load(file),
                                              resources_path=path.join(constants.RESOURCE_PATH,
                                                                       'themes', 'overlayer'))
        except FileNotFoundError as e:
            logger.error(e.strerror, e.filename, title='in menu loading')

        try:
            with open(path.join(constants.RESOURCE_PATH, 'themes', 'overlay', 'theme.json'),
                      'r') as file:
                Themes.overlayTheme = Theme(json.load(file),
                                            resources_path=path.join(constants.RESOURCE_PATH,
                                                                     'themes', 'overlay'))
        except FileNotFoundError as e:
            logger.error(e.strerror, e.filename, title="in overlay loading")


class FixButton(Button):
    def __init__(self, *args, fixed_width=500, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixed_width = fixed_width

    def compute_size(self):
        # Treat the height of the label as ascent + descent
        font = self._label.document.get_font()
        height = font.ascent - font.descent

        return self._button.get_needed_size(self.fixed_width, height)


class FixOneTimeButton(OneTimeButton):
    def __init__(self, *args, fixed_width=500, active=True, **kwargs):
        self.fixed_width = fixed_width
        self.active = active
        super().__init__(*args, **kwargs)

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False
        if self.is_pressed:
            self.change_state()

    def compute_size(self):
        # Treat the height of the label as ascent + descent
        font = self._label.document.get_font()
        height = font.ascent - font.descent

        return self._button.get_needed_size(self.fixed_width, height)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.active:
            self.change_state()

    def on_mouse_release(self, x, y, button, modifiers):
        if self.active:
            if self.is_pressed:
                self.change_state()

                # If mouse is still hovering us, signal on_release
                if self.hit_test(x, y):
                    self.on_release(self._is_pressed)

    def get_path(self):
        btn_path = ['button']
        if not self.active:
            btn_path.append('inactive')
        elif self.is_pressed:
            btn_path.append('down')
        else:
            btn_path.append('up')
        return btn_path


class FullFrame(Frame):
    def __init__(self, window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window = window

    def compute_size(self):
        return self._frame.get_needed_size(self.window.width, self.window.height)


class FixedFrame(Frame):
    def __init__(self, fixed_width, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixed_width = fixed_width

    def compute_size(self):
        self.content.compute_size()
        return self._frame.get_needed_size(self.fixed_width, self.content.height)


class PasswordInput(TextInput):
    def __init__(self, text="", *args, **kwargs):
        super().__init__(text=text, *args, **kwargs)

        self._document = pyglet.text.document.UnformattedDocument('*' * len(text))
        self.pass_document = pyglet.text.document.UnformattedDocument(text)

        # graphics loaded in state "writing"
        self.pass_text_layout = None
        self.pass_caret = None

    def _load_writing(self, theme):
        needed_width, needed_height = self._compute_needed_size()

        self._text_layout = pyglet.text.layout.IncrementalTextLayout(self._document, needed_width,
                                                                     needed_height, multiline=False,
                                                                     **self.get_batch('foreground'))

        self._caret = pyglet.text.caret.Caret(self._text_layout, color=theme['gui_color'][0:3])
        self._caret.visible = True
        self._caret.mark = 0
        self._caret.position = len(self._document.text)

        self.pass_text_layout = pyglet.text.layout.IncrementalTextLayout(self.pass_document,
                                                                         needed_width,
                                                                         needed_height,
                                                                         multiline=False)

        self.pass_caret = pyglet.text.caret.Caret(self.pass_text_layout,
                                                  color=theme['gui_color'][0:3])
        self.pass_caret.visible = True
        self.pass_caret.mark = 0
        self.pass_caret.position = len(self.pass_document.text)

    def _unload_writing(self):
        self._caret.delete()  # it should be .unload(), but Caret does not have it.
        self._document.remove_handlers(self._text_layout)
        self._text_layout.delete()  # it should also be .unload().
        self._caret = self._text_layout = None

        self.pass_caret.delete()  # it should be .unload(), but Caret does not have it.
        self.pass_document.remove_handlers(self.pass_text_layout)
        self.pass_text_layout.delete()  # it should also be .unload().
        self.pass_caret = self.pass_text_layout = None

    def get_text(self):
        return self._document.text

    def get_password(self):
        return self.pass_document.text

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        pass

    def on_mouse_press(self, x, y, button, modifiers):
        pass

    def on_text(self, text):
        assert self.is_focus()

        self._caret.on_text('*' * len(text))
        if self._max_length and len(self._document.text) > self._max_length:
            self._document.text = self._document.text[:self._max_length]
            self._caret.mark = self._caret.position = self._max_length

        self.pass_caret.on_text(text)
        if self._max_length and len(self.pass_document.text) > self._max_length:
            self.pass_document.text = self.pass_document.text[:self._max_length]
            self.pass_caret.mark = self.pass_caret.position = self._max_length

        return pyglet.event.EVENT_HANDLED

    def on_text_motion(self, motion):
        assert self.is_focus()
        self.pass_caret.on_text_motion(motion)
        return self._caret.on_text_motion(motion)

    def on_text_motion_select(self, motion):
        assert self.is_focus()
        self.pass_caret.on_text_motion_select(motion)
        return self._caret.on_text_motion_select(motion)

    def set_text(self, text):
        self._document.text = '*' * len(text)
        if self.is_focus():
            self._caret.mark = self._caret.position = len(self._document.text)
        else:
            self._label.text = '*' * len(text)

        self.pass_document.text = text
        if self.is_focus():
            self.pass_caret.mark = self.pass_caret.position = len(self.pass_document.text)
