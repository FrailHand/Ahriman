from os import path

import pyglet
from pyglet.gl import *

from ahriman import constants
from ahriman import logger
from ahriman.activities import Activity
from ahriman.activities.gameActivity import GameActivity
from ahriman.game import Game
from ahriman.game import TextureManager


class LoadingActivity(Activity):
    def __init__(self, window, reconnecting=False):
        super().__init__(window)

        self.reconnecting = reconnecting

        self.batch = pyglet.graphics.Batch()
        self.image = pyglet.image.load(
            path.join(constants.RESOURCE_PATH, 'backgrounds', 'loading.png'))
        self.background = pyglet.sprite.Sprite(self.image, usage='static')
        self.update_bg()

        self.window.gameClient.start_game()
        try:
            TextureManager.load_textures()
            Game.parse_logic()
        except Exception as e:
            self.window.fire_event((constants.Event.WINDOW_EVENT, constants.WindowEvent.ERROR, str(e)), priority=True)

    def on_resize(self, width, height):
        self.update_bg()

    def draw(self):
        self.window.draw_2D()
        self.background.draw()

    def event_handler(self, event):
        if event[0] == constants.Event.GAME_EVENT:

            if event[1] == constants.GameEvent.CONNECTION:
                if event[2].connection:
                    logger.info(event[2].player.playerID, title='player connected')
                else:
                    logger.info(event[2].player.playerID, title='player disconnected')

            elif event[1] == constants.GameEvent.ROOM_FULL:
                logger.confirm('all players connected')
                player_names = [''] * event[2].roomSize
                for player in event[2].player:
                    player_names[player.playerNum] = player.playerID
                self.window.change_activity(
                    GameActivity(self.window, player_names, reconnection=self.reconnecting),
                    fade_out=True, fade_in=True)

            else:
                super().event_handler(event)
        else:
            super().event_handler(event)

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
