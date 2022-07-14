import pyglet

from ahriman import constants
from ahriman.game.card import Card


class CardHolder:
    CARD_WIDTH = 120
    CARD_DEPTH = 20
    CARD_TRANSITION = constants.CARD_ANIMATION_DURATION / 3

    def __init__(self, window):
        self.win = window
        self.batch = pyglet.graphics.Batch()

        self.height_offset = self.win.height - CardHolder.CARD_WIDTH + CardHolder.CARD_DEPTH
        self.width_offset = 0

        self.cards = []

    def card_coord(self, idx, cy):
        return idx * CardHolder.CARD_WIDTH + self.width_offset, self.height_offset + cy

    def update(self):
        for card in self.cards:
            card.update()

    def delete(self):
        for card in self.cards:
            card.delete()

    def empty_hand(self):
        for card in self.cards:
            card.position.parabolic(2 * constants.CARD_ANIMATION_DURATION, CardHolder.CARD_TRANSITION,
                                    (0, CardHolder.CARD_WIDTH), relative=True, on_end=card.delete)

    def select_card(self, card, enter=True, full=False):
        dy = CardHolder.CARD_DEPTH

        if not full:
            dy = dy / 2

        if enter:
            dy = -dy

        self.cards[card].position.parabolic(constants.CARD_ANIMATION_DURATION, CardHolder.CARD_TRANSITION,
                                            (0, dy), relative=True)

    def draw_hand(self, card_dicts):
        self.cards = []
        number = len(card_dicts)
        self.width_offset = (self.win.width - number * CardHolder.CARD_WIDTH) / 2

        for idx, card in enumerate(card_dicts):
            card_coord = self.card_coord(idx, CardHolder.CARD_WIDTH)
            new_card = Card(self.batch, card_coord, card, CardHolder.CARD_WIDTH)
            self.cards.append(new_card)
            new_card.position.parabolic(2 * constants.CARD_ANIMATION_DURATION, CardHolder.CARD_TRANSITION,
                                        (0, -CardHolder.CARD_WIDTH), relative=True)

    def draw(self):
        self.win.draw_2D()
        self.batch.draw()

    def mouse_to_card(self, x, y):

        if not all((self.width_offset < x < self.win.width - self.width_offset, y > self.height_offset)):
            return None

        card = int((x - self.width_offset) // CardHolder.CARD_WIDTH)
        if self.cards[card] is not None:
            return card

        return None
