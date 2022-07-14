import queue
from enum import Enum, auto
from os import path

import pyglet
from pyglet.gl import *
from pyglet.window import key

from ahriman import constants
from ahriman import strings
from ahriman.activities.introActivity import IntroActivity
from ahriman.activities.popupActivity import PopupActivity
from ahriman.communication import GameClient


class Window(pyglet.window.Window):
    """application window showing one activity at a time and interacting with the user"""

    class Fading(Enum):
        FADE_OUT = auto()
        FADE_IN = auto()
        NONE = auto()
        DONE = auto()

    def __init__(self):
        super().__init__(caption=strings.WINDOW_CAPTION, resizable=False, fullscreen=False)

        if not self.fullscreen:
            self.set_size(*constants.DEFAULT_WIN_SIZE)

        # load the icon image
        icon1 = pyglet.image.load(path.join(constants.RESOURCE_PATH, 'icons', '16x16.png'))
        icon2 = pyglet.image.load(path.join(constants.RESOURCE_PATH, 'icons', '128x128.png'))
        self.set_icon(icon1, icon2)

        # allows constant access to keyboard state
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)

        # initial mouse state
        self.mouse_in = False
        self.mouse_dragging = False

        # initial activity transition state
        self.fading = Window.Fading.NONE
        self.fading_alpha = 0
        self.next_activity = None
        self.error_state = None

        # TODO put a very nice cursor
        # cur_image = pyglet.image.load(path.join(constants.resource_dir, 'cursor.png'))
        # cursor = pyglet.window.ImageMouseCursor(cur_image, 6, 32)
        # self.set_mouse_cursor(cursor)

        self.event_queue = queue.Queue()
        self.priority_queue = queue.Queue()
        self.gameClient = GameClient(self)

        self.activity = IntroActivity(window=self)

        pyglet.clock.schedule_interval(self.update, interval=1 / 120)

    def fire_event(self, event, priority=False):
        """
        put an event in the queue
        event: (tuple) with event[0] (constants.event)
        priority: (int) priority level, lowest = most important
        """
        if priority:
            self.priority_queue.put(event)
        else:
            self.event_queue.put(event)

    @property
    def mouse(self):
        return self._mouse_x, self._mouse_y

    def change_activity(self, new_activity, fade_out=False, fade_in=False):
        if fade_out:
            # do not change the activity immediately, but first fade out the present one
            self.fading = Window.Fading.FADE_OUT
            # save the activity to be displayed after the transition (delete the old one)
            if self.next_activity is not None:
                self.next_activity[0].delete()
            self.next_activity = (new_activity, fade_in)

        else:
            if fade_in:
                # initiate the fade-in process
                self.fading = Window.Fading.FADE_IN
                self.fading_alpha = 1
            else:
                self.fading = Window.Fading.NONE

            # delete the current activity and replace it with the new one
            self.activity.delete()
            del self.activity
            self.next_activity = None
            self.activity = new_activity

    def force_activity(self, new_activity):
        # force change the activity without deleting the current one
        # used by overlays (old activity remains 'sleeping' in background, can be brought back)
        if self.next_activity is not None:
            self.next_activity = (new_activity, self.next_activity[1])

        else:
            self.activity = new_activity

    # a bunch of handlers for keys/mouse/window events
    def on_key_press(self, KEY, _MOD):
        if self.fading == Window.Fading.NONE:
            self.activity.on_key_press(KEY, _MOD)

    # noinspection PyMethodOverriding
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.activity.on_mouse_scroll(x, y, scroll_x, scroll_y)

    # noinspection PyMethodOverriding
    def on_mouse_motion(self, x, y, dx, dy):
        self.activity.on_mouse_move(x, y)

    # noinspection PyMethodOverriding
    def on_mouse_enter(self, x, y):
        self.mouse_in = True

    # noinspection PyMethodOverriding
    def on_mouse_leave(self, x, y):
        self.mouse_in = False

    # noinspection PyMethodOverriding
    def on_mouse_release(self, x, y, button, modifiers):
        if self.fading == Window.Fading.NONE:
            self.activity.on_mouse_release(x, y, button, modifiers)
        self.mouse_dragging = False

    # noinspection PyMethodOverriding
    def on_mouse_press(self, x, y, button, modifiers):
        if self.fading == Window.Fading.NONE:
            self.activity.on_mouse_press(x, y, button, modifiers)

    # noinspection PyMethodOverriding
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.mouse_dragging = True
        self.activity.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def on_resize(self, width, height):
        super().on_resize(width, height)
        self.activity.on_resize(width, height)

    def update(self, dt):
        try:
            # first check the event queue until it is empty
            while True:
                try:
                    event = self.priority_queue.get(block=False)
                except queue.Empty:
                    event = self.event_queue.get(block=False)

                # these events must be handled by the window itself
                if event[0] == constants.Event.WINDOW_EVENT:
                    if event[1] == constants.WindowEvent.ERROR:
                        bg_activity = self.activity
                        if self.next_activity is not None:
                            bg_activity = self.next_activity[0]

                        self.force_activity(
                            PopupActivity(self, bg_activity, (event[2],), on_true=self.close,
                                          resume_on_event=False, ok_message=strings.QUIT_BUTTON))
                        self.error_state = True

                    elif event[1] == constants.WindowEvent.FADE_END:
                        # transition ended, switch to the next activity
                        self.change_activity(new_activity=self.next_activity[0],
                                             fade_in=self.next_activity[1])

                elif not self.error_state:
                    # event must be handled by the activity
                    if self.fading == Window.Fading.FADE_OUT:
                        # if fading out, redirect events to the future activity
                        self.next_activity[0].event_handler(event)
                    else:
                        self.activity.event_handler(event)
        except queue.Empty:
            pass

        # update the transition opacity for fades
        if self.fading == Window.Fading.FADE_OUT:
            new_alpha = self.fading_alpha + dt * constants.FADING_SPEED
            if new_alpha > 1:
                new_alpha = 1
                self.fire_event((constants.Event.WINDOW_EVENT, constants.WindowEvent.FADE_END))
                # fading must end, but not to none else opacity will come back to 1 immediately
                self.fading = Window.Fading.DONE
            self.fading_alpha = new_alpha

        elif self.fading == Window.Fading.FADE_IN:
            new_alpha = self.fading_alpha - dt * constants.FADING_SPEED
            if new_alpha < 0:
                new_alpha = 0
                self.fading = Window.Fading.NONE
            self.fading_alpha = new_alpha

        self.activity.update(dt)

    # noinspection PyMethodOverriding
    def on_draw(self):
        # draw the foreground activity
        self.clear()
        self.activity.draw()

        # if transition, draw a rectangle in superposition for the fading effect
        if self.fading != Window.Fading.NONE:
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glColor4f(*constants.FADING_COLOR, self.fading_alpha)
            glBegin(GL_QUADS)
            glVertex2f(0, 0)
            glVertex2f(self.width, 0)
            glVertex2f(self.width, self.height)
            glVertex2f(0, self.height)
            glEnd()

    def draw_2D(self):
        """
        enable 2D rendering (for menus, etc)
        """
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, self.width, 0, self.height)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
