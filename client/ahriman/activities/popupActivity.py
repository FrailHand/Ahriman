import pyglet
from pyglet.gl import *
from pyglet.window import key
from pyglet_gui.containers import Spacer
from pyglet_gui.gui import *

from ahriman import logger
from ahriman import strings
from ahriman.activities.customGUIs import FixOneTimeButton, FullFrame, Themes
from ahriman.activities.overLayerActivity import OverLayerActivity


class PopupActivity(OverLayerActivity):
    def __init__(self, window, bg_activity, message, on_true=None, on_false=None, no_option=False,
                 resume_on_event=True, ok_message=None):
        super().__init__(window, bg_activity)

        if on_true is None:
            on_true = self.resume
        if on_false is None:
            on_false = self.resume
        self.no_option = no_option
        self.on_true = on_true
        self.on_false = on_false

        self.resume_on_event = resume_on_event

        self.batch = pyglet.graphics.Batch()
        self.on_false = on_false
        self.on_true = on_true

        self.h_layout = HorizontalContainer([])
        self.v_layout = VerticalContainer([])
        self.content = FullFrame(self.window, self.v_layout)

        self.man = Manager(self.content, window=self.window, batch=self.batch, anchor=ANCHOR_CENTER,
                           theme=Themes.overLayerTheme, is_movable=False)

        for element in message:
            title = Label(element)
            self.v_layout.add(title)
        self.v_layout.add(Spacer(min_height=20))
        self.v_layout.add(self.h_layout)

        if no_option:
            self.yesButton = FixOneTimeButton(strings.YES_BUTTON, fixed_width=70,
                                              on_release=self.click_yes)
            self.h_layout.add(self.yesButton)
            self.h_layout.add(Spacer(min_width=20))
            self.noButton = FixOneTimeButton(strings.NO_BUTTON, fixed_width=70,
                                             on_release=self.click_no)
            self.h_layout.add(self.noButton)
        else:
            if ok_message is None:
                ok_message = strings.OK_BUTTON
            self.yesButton = FixOneTimeButton(ok_message, fixed_width=100,
                                              on_release=self.click_yes)
            self.h_layout.add(self.yesButton)

    def on_key_press(self, KEY, _MOD):
        if KEY == key.ESCAPE:
            if self.no_option:
                self.click_no()
            else:
                self.click_yes()
        elif KEY == key.ENTER or KEY == key.NUM_ENTER:
            self.click_yes()

    def delete_self(self):
        self.man.delete()

    def event_handler(self, event):
        if self.resume_on_event:
            super().event_handler(event)
        else:
            logger.warning(event, title='event ignored')

    def draw(self):
        super().draw()
        self.window.draw_2D()

        self.batch.draw()

    def click_no(self, is_clicked=False):
        self.on_false()

    def click_yes(self, is_clicked=False):
        self.on_true()
