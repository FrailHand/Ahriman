import pickle

from pyglet.window import key

from ahriman import constants, logger
from ahriman import strings
from ahriman.game import Game
from ahriman.game import Overlay
from . import Activity
from .popupActivity import PopupActivity
from .timerActivity import TimerActivity


class GameActivity(Activity):
    """game view containing the board and an overlay"""

    def __init__(self, window, player_names, reconnection=False):
        super().__init__(window)

        player_num = self.window.gameClient.playerNum
        self.reconnection = reconnection

        self.game = Game(window, player_num)

        self.overlay = Overlay(window, player_names)

        if player_num == 0 and not reconnection:
            self.game.init_board()
            self.send_state()
            self.overlay.update(self.game.state_dict)

    def on_mouse_move(self, x, y):
        self.game.on_mouse_move(x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        if not self.overlay.is_inside(x, y) and button == 1:
            pass

    def on_mouse_release(self, x, y, button, modifiers):
        if not self.overlay.is_inside(x, y) and button == 1:
            if not self.window.mouse_dragging:
                self.game.on_mouse_click(x, y)
                self.overlay.update(self.game.state_dict)

    def on_mouse_scroll(self, mouse_x, mouse_y, scroll_x, scroll_y):
        self.game.on_mouse_scroll(mouse_x, mouse_y, scroll_x, scroll_y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.game.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def on_resize(self, width, height):
        self.game.on_resize(width, height)

    def update(self, dt, bg=False):
        self.game.update(dt, move=not self.overlay.is_inside(*self.window.mouse) and not bg)

    def draw(self):
        self.game.draw()
        self.overlay.draw()

    def event_handler(self, event):

        if event[0] == constants.Event.GAME_EVENT:

            if event[1] == constants.GameEvent.CONNECTION:
                if event[2].connection:
                    super().event_handler(event)
                else:
                    from .homeActivity import HomeActivity
                    back = lambda: self.window.change_activity(HomeActivity(self.window),
                                                               fade_out=True, fade_in=True)

                    player_num = event[2].player.playerNum
                    self.game.disconnect(player_num)

                    self.window.force_activity(
                        TimerActivity(self.window, self, strings.PLAYER_DISCONNECTED_TIMER,
                                      yes_title=strings.LEAVE_BUTTON,
                                      timer=constants.LEAVING_TIMEOUT, on_true=back,
                                      resume_on_event=False))

            elif event[1] == constants.GameEvent.ACTION:

                if event[2] == constants.GameAction.TURN_DONE:
                    self.game.validate_turn(player_num=event[3])

                else:
                    if not self.game.perform(player=event[3], action=event[2], coord=event[4]):
                        self.hack_detected()
                    else:
                        self.overlay.update(self.game.state_dict)

            elif event[1] == constants.GameEvent.BOARD_STATE:
                if (not self.game.initialized) and (event[2].issuer == 0 or self.reconnection):
                    load_state = pickle.loads(event[2].state)
                    self.game.load_state(load_state)
                    self.overlay.update(self.game.state_dict)

                else:
                    self.hack_detected()
                    return

            else:
                super().event_handler(event)

        elif event[0] == constants.Event.PLAYER_EVENT:
            if event[1] == constants.PlayerEvent.END_TURN:
                self.game.validate_turn()

                self.overlay.update(self.game.state_dict)

            elif event[1] == constants.PlayerEvent.SYMBOLS_TOGGLE:
                self.game.graphic_board.toggle_symbols(event[2])

            else:
                super().event_handler(event)

        else:
            super().event_handler(event)

    def send_state(self):
        byte_state = pickle.dumps(self.game.logic)
        self.window.gameClient.send_game_state(byte_state)

    def on_key_press(self, KEY, _MOD):
        if KEY == key.ESCAPE:
            from ahriman.activities.homeActivity import HomeActivity
            back = lambda: self.window.change_activity(HomeActivity(self.window), fade_out=True,
                                                       fade_in=True)

            self.window.force_activity(
                TimerActivity(self.window, self, strings.QUIT_POPUP_MESSAGE, on_true=back,
                              no_option=True, timer=constants.LEAVING_TIMEOUT,
                              resume_on_event=True))

    def delete(self):
        self.window.gameClient.quit()
        self.overlay.delete()
        self.game.delete()

    def hack_detected(self):
        logger.warning('hack detected')
        from ahriman.activities.homeActivity import HomeActivity
        back = lambda: self.window.change_activity(HomeActivity(self.window), fade_out=True,
                                                   fade_in=True)
        self.window.force_activity(
            PopupActivity(self.window, self, strings.HACK_POPUP, on_true=back,
                          resume_on_event=False))  # TODO send a report message to the server ?
