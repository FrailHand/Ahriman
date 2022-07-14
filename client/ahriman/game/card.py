from ahriman.game.animator import Animator
from .gameTex import *


class Card:

    def __init__(self, batch, position, card_dict, width):
        self.texture = card_dict['texture']
        self.batch = batch
        self.texture_manager = None
        self.width = width

        x, y = position
        coords = ('v2f', (
            x, y,
            x + self.width, y,
            x + self.width, y + self.width,
            x, y + self.width
        ))
        self.texture_manager = TextureManager(self.texture, coords, self.batch)

        self.position = Animator((x, y), self._set_position)

    def update(self):
        self.texture_manager.update()
        self.position.update()

    def delete(self):
        self.texture_manager.delete()

    def set_object(self, card_dict):
        self.texture = card_dict['texture']

    def set_position(self, position):
        self.position.value = position

    def _set_position(self, position):
        x, y = position
        move_coords = (
            x, y,
            x + self.width, y,
            x + self.width, y + self.width,
            x, y + self.width
        )
        self.texture_manager.move(move_coords)
