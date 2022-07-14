from pyglet.gl import *
from pyglet_gui.buttons import Checkbox
from pyglet_gui.constants import ANCHOR_TOP_LEFT, ANCHOR_TOP_RIGHT, ANCHOR_BOTTOM_RIGHT
from pyglet_gui.constants import HALIGN_LEFT, HALIGN_RIGHT
from pyglet_gui.containers import Spacer
from pyglet_gui.containers import VerticalContainer, HorizontalContainer
from pyglet_gui.gui import SectionHeader, Label
from pyglet_gui.manager import Manager

from ahriman import strings
from ahriman.activities.customGUIs import *


class Overlay:
    """game overlay with GUIs and text"""

    def __init__(self, window, player_names):
        self.window = window
        self.batch = pyglet.graphics.Batch()

        self.end_turn_button = FixOneTimeButton(label=strings.END_TURN_BUTTON_INACTIVE,
                                                active=False, fixed_width=100,
                                                on_release=self.press_end_turn)

        self.symbol_toggle = Checkbox(label=strings.SYMBOL_CHECKBOX, on_press=self.press_symbol_toggle,
                                      align=HALIGN_LEFT)

        self.stats = (
            StatsCounter(HALIGN_LEFT),
            StatsCounter(HALIGN_RIGHT)
        )

        containers = (
            VerticalContainer(
                [SectionHeader(player_names[0], align=HALIGN_LEFT), Spacer(min_height=20),
                 self.stats[0].container], align=HALIGN_LEFT),
            VerticalContainer(
                [SectionHeader(player_names[1], align=HALIGN_RIGHT), Spacer(min_height=20),
                 self.stats[1].container], align=HALIGN_RIGHT),
            VerticalContainer([self.symbol_toggle, self.end_turn_button],
                              align=HALIGN_RIGHT)
        )

        frames = (
            FixedFrame(150, containers[0], anchor=ANCHOR_TOP_LEFT),
            FixedFrame(150, containers[1], anchor=ANCHOR_TOP_RIGHT),
            FixedFrame(150, containers[2], anchor=ANCHOR_BOTTOM_RIGHT)
        )

        self.managers = [
            Manager(frames[0], window=self.window, batch=self.batch, anchor=ANCHOR_TOP_LEFT,
                    theme=Themes.overlayTheme, is_movable=False),
            Manager(frames[1], window=self.window, batch=self.batch, anchor=ANCHOR_TOP_RIGHT,
                    theme=Themes.overlayTheme, is_movable=False),
            Manager(frames[2], window=self.window, batch=self.batch, anchor=ANCHOR_BOTTOM_RIGHT,
                    theme=Themes.overlayTheme, is_movable=False)
        ]

    def activate_end_turn(self, active=True):
        if active:
            self.end_turn_button.label = strings.END_TURN_BUTTON_ACTIVE
            self.end_turn_button.activate()
            self.end_turn_button.reload()
            self.end_turn_button.reset_size()

        else:
            self.end_turn_button.label = strings.END_TURN_BUTTON_INACTIVE
            self.end_turn_button.deactivate()
            self.end_turn_button.reload()
            self.end_turn_button.reset_size()

    def is_inside(self, x, y):
        return any(manager.is_inside(x, y) for manager in self.managers)

    def press_end_turn(self, is_pressed):
        self.window.fire_event((constants.Event.PLAYER_EVENT, constants.PlayerEvent.END_TURN))

    def press_symbol_toggle(self, is_pressed):
        self.window.fire_event((constants.Event.PLAYER_EVENT, constants.PlayerEvent.SYMBOLS_TOGGLE, is_pressed))

    def draw(self):
        self.window.draw_2D()
        self.batch.draw()

    def delete(self):
        for manager in self.managers:
            manager.delete()

    def update(self, state_dict):
        self.activate_end_turn(state_dict['end_turn_enabled'])
        for index, stat in enumerate(self.stats):
            stat.update(state_dict, index)

    def update_stats(self, victory):
        for id, points in enumerate(victory):
            self.stats[id].update(points)


class StatsCounter:
    def __init__(self, align):
        tiles_title = Label('T:')
        self.tiles_label = Label('0')
        tiles_container = HorizontalContainer([tiles_title, self.tiles_label], align=HALIGN_LEFT)
        captures_title = Label('C:')
        self.captures_label = Label('0')
        captures_container = HorizontalContainer([captures_title, self.captures_label], align=HALIGN_LEFT)
        victory_title = Label('V:')
        self.victory_label = Label('0')
        victory_container = HorizontalContainer([victory_title, self.victory_label], align=HALIGN_LEFT)

        self.container = VerticalContainer([tiles_container,
                                            captures_container,
                                            victory_container], align=align)

    def update(self, state_dict, index):
        self.tiles_label.set_text(str(state_dict['tiles'][index]))
        self.captures_label.set_text(str(state_dict['captures'][index]))
        self.victory_label.set_text(str(state_dict['points'][index]))
