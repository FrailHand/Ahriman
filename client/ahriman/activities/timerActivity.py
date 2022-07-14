import math
import time

from ahriman import constants
from ahriman import logger
from ahriman import strings
from ahriman.activities.popupActivity import PopupActivity


class TimerActivity(PopupActivity):
    def __init__(self, window, bg_activity, message, on_true=None, on_false=None, no_option=False,
                 timer=10, yes_title=strings.OK_BUTTON, no_title=strings.CANCEL_BUTTON,
                 resume_on_event=False):

        super().__init__(window, bg_activity, message, on_true, on_false, no_option,
                         resume_on_event)

        self.yesButton.label = str(timer)
        self.yesButton.deactivate()
        self.yesButton.reload()
        self.yesButton.reset_size()

        self.no_title = no_title
        self.yes_title = yes_title

        if self.no_option:
            self.noButton.label = self.no_title
            self.noButton.reload()
            self.noButton.reset_size()

        self.timer = timer
        self.current = timer
        self.initial = time.time()

    def update(self, dt, bg=False):
        super().update(dt, bg=bg)
        if self.current > 0:
            self.current = self.timer - math.floor(time.time() - self.initial)
        if self.current > 0:
            self.yesButton.label = str(self.current)
            self.yesButton.reload()
            self.yesButton.reset_size()
        else:
            self.yesButton.label = self.yes_title
            self.yesButton.activate()
            self.yesButton.reload()
            self.yesButton.reset_size()

    def event_handler(self, event):
        if self.resume_on_event:
            super().event_handler(event)
        else:
            if event[0] == constants.Event.GAME_EVENT:

                if event[1] == constants.GameEvent.ROOM_FULL:
                    self.bg_activity.send_state()
                    self.resume()

                elif event[1] == constants.GameEvent.CONNECTION:
                    if event[2].connection:
                        logger.info(event[2].player.playerID, title='player connected')

                else:
                    super().event_handler(event)

            else:
                super().event_handler(event)

    def click_yes(self, is_clicked=False):
        if self.yesButton.active:
            super().click_yes(is_clicked)
