from abc import ABCMeta
from abc import abstractmethod

from pyglet.window import key

from ahriman import logger
from ahriman import strings


class Activity(metaclass=ABCMeta):
    """interface defining base interactions with the window for different views"""

    def __init__(self, window):
        self.window = window

    def on_mouse_move(self, x, y):
        pass

    def on_mouse_scroll(self, mouse_x, mouse_y, scroll_x, scroll_y):
        pass

    def on_mouse_release(self, x, y, button, modifiers):
        pass

    def on_mouse_press(self, x, y, button, modifiers):
        pass

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        pass

    def on_resize(self, width, height):
        pass

    def update(self, dt, bg=False):
        pass

    def event_handler(self, event):
        logger.warning(event, title="unhandled event in {}".format(self))

    def on_key_press(self, KEY, _MOD):
        if KEY == key.ESCAPE:
            from .popupActivity import PopupActivity
            self.window.force_activity(PopupActivity(self.window, self, strings.QUIT_POPUP_MESSAGE,
                                                     on_true=self.window.close, no_option=True))

    @abstractmethod
    def draw(self):
        pass

    @abstractmethod
    def delete(self):
        pass

    def __repr__(self):
        return self.__class__.__name__
