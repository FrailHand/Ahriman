import json
import random

from ahriman import constants
from ahriman import logger
from ahriman.constants import GameAction
from ahriman.game import Board
from ahriman.game.cardholder import CardHolder
from .logic import Logic


class Game:
    OBJECTS_DICT = {}
    RULES_DICT = {}

    @staticmethod
    def parse_logic():
        if len(Game.OBJECTS_DICT) == 0:
            Game.parse_objects()
            Game.parse_rules()

    @staticmethod
    def parse_objects():
        try:
            with open(constants.LOGIC_OBJECTS, 'r') as file:
                Game.OBJECTS_DICT = json.load(file)

            try:
                for name_tile, tile in Game.OBJECTS_DICT['tiles'].items():
                    if len(tile['resources']) > 1:
                        logger.error('multiple resource on one tile', name_tile)
                        raise NotImplementedError('multiple resource on one tile')

                    Game.convert_textures(tile)

                    if len(tile['resources']) > 0:
                        tile['textures']['symbol'] = '_'.join(('symbols', list(tile['resources'])[0]))

                for name_node, node in Game.OBJECTS_DICT['nodes'].items():
                    Game.convert_textures(node)

                for name_card, card in Game.OBJECTS_DICT['cards'].items():
                    card['texture'] = '_'.join(('cards', name_card))

            except KeyError as e:
                logger.error('invalid objects.json - ', str(e))
                raise KeyError('invalid objects.json')

            logger.confirm('objects successfully loaded !')

        except FileNotFoundError as e:
            logger.error(e, title="in tiles parsing")
            raise e

    @staticmethod
    def convert_textures(board_object_dict):
        for tex_group, tex_name in board_object_dict['textures'].items():
            board_object_dict['textures'][tex_group] = '_'.join((constants.TEXTURE_CLASS[tex_group], tex_name))

    @staticmethod
    def parse_rules():
        try:
            with open(constants.LOGIC_RULES, 'r') as file:
                Game.RULES_DICT = json.load(file)

            logger.confirm('rules successfully loaded !')

        except FileNotFoundError as e:
            logger.error(e, title="in rules parsing")
            raise e

    def __init__(self, window, player_num, total_players=2):
        self.logic = Logic(total_players)

        self.player_num = player_num

        self.initialized = False
        self.send_game_action = window.gameClient.send_game_action

        self.graphic_board = Board(window, rows=Game.RULES_DICT['board']['rows'],
                                   cols=Game.RULES_DICT['board']['cols'])
        self.card_holder = CardHolder(window)
        # TODO remove this and correctly load the cards
        self.card_holder.draw_hand([Game.OBJECTS_DICT['cards']['flag']] * 3)

        self.highlighted_tile = None
        self.selected_tile = None
        self.last_click = 0
        self.highlighted_node = None
        self.selected_node = None
        self.highlighted_card = None
        self.selected_card = None

        self.selected_actions = [None] * total_players

    @property
    def state_dict(self):
        end_turn = self.selected_actions[self.player_num] is not None and not self.logic.turn_validated[self.player_num]
        return {
            'tiles': self.logic.owned_tiles,
            'captures': self.logic.captures,
            'points': self.logic.victory_points,
            'end_turn_enabled': end_turn,
        }

    def validate_turn(self, player_num=None):
        if player_num is None:
            if self.selected_actions[self.player_num] is not None:
                self.logic.turn_validated[self.player_num] = True
                self.send_game_action(action=constants.GameAction.TURN_DONE)

        else:
            if self.logic.turn_validated[player_num]:
                logger.warning('a player validated his turn twice')
            self.logic.turn_validated[player_num] = True

        if all(self.logic.turn_validated):
            self.send_game_action(action=self.selected_actions[self.player_num][0],
                                  coord=self.selected_actions[self.player_num][1])

    def perform(self, player, action, coord):
        try:
            if not self.logic.can_perform(player, action, coord):
                return False
        except TypeError:
            return False

        self.selected_actions[player] = (action, coord)

        if not any([action is None for action in self.selected_actions]):
            to_update = self.logic.resolve(self.selected_actions)
            for coord in to_update:
                self.graphic_board[coord].change_owner(self.logic[coord].owner)
                # TODO animate the turn resolution

            self.selected_actions = [None] * self.logic.total_players
            self.select_node(None)

        return True

    def disconnect(self, player):
        self.logic.turn_validated[player] = False

    def add_node(self, coord, owner=-2):
        self.graphic_board.nodes[coord].set_object(
            Game.OBJECTS_DICT['nodes'][Game.RULES_DICT['board']['node_object']], -2)
        self.logic.add_node(coord, owner)

    def add_tile(self, tile_coord, tile_name, owner=-1):
        self.graphic_board.tiles[tile_coord].set_object(Game.OBJECTS_DICT['tiles'][tile_name], owner)
        self.logic.add_tile(tile_coord, tile_name, owner)

    def init_board(self):
        # TODO is this half splitting necessary? NO
        total_half = (len(self.graphic_board.tiles)) // 2
        total_weight = sum(Game.RULES_DICT['board']['init'].values())

        left_half = []
        for tile, weight in Game.RULES_DICT['board']['init'].items():
            stack = [tile] * int(round(total_half * weight / total_weight))
            left_half.extend(stack)

        if len(left_half) < total_half:
            left_half.extend(
                [list(Game.RULES_DICT['board']['init'])[0]] * (total_half - len(left_half)))
        elif len(left_half) > total_half:
            left_half.pop()

        right_half = list(left_half)
        random.shuffle(right_half)
        random.shuffle(left_half)

        def put_left(tile_coord):
            put_tile = left_half.pop()
            self.add_tile(tile_coord, put_tile)

        def put_right(tile_coord):
            put_tile = right_half.pop()
            self.add_tile(tile_coord, put_tile)

        for coord in self.graphic_board.tiles.keys():
            if coord[1] == 2 * coord[0] + 1 - self.graphic_board.cols:
                if coord[1] < self.graphic_board.rows - 1:
                    put_right(coord)
                elif coord[1] > self.graphic_board.rows - 1:
                    put_left(coord)
                else:
                    self.add_tile(coord, Game.RULES_DICT['board']['fill'])
            elif coord[1] < 2 * coord[0] + 1 - self.graphic_board.cols:
                put_right(coord)
            elif coord[1] > 2 * coord[0] + 1 - self.graphic_board.cols or coord[1] > self.graphic_board.rows:
                put_left(coord)

        for coord in self.graphic_board.nodes.keys():
            self.graphic_board.nodes[coord].set_object(
                Game.OBJECTS_DICT['nodes'][Game.RULES_DICT['board']['node_object']], -2)
            self.add_node(coord)

        self.initialized = True

    def select_tile(self, tile):
        if self.selected_tile != tile:
            if self.selected_tile is not None:
                self.graphic_board[self.selected_tile].change_color(
                    constants.TILE_BASE_COLOR)
                self.graphic_board[self.selected_tile].set_select_tex('none')

            if tile is not None:
                self.graphic_board[tile].change_color(constants.TILE_SELECT_COLOR)
                self.graphic_board[tile].set_select_tex('UI_select')

            self.selected_tile = tile

    def select_node(self, node):
        if self.selected_node != node:
            if self.selected_node is not None:
                self.graphic_board[self.selected_node].change_color(
                    constants.TILE_BASE_COLOR)
                self.graphic_board[self.selected_node].set_select_tex('none')

            if node is not None:
                self.graphic_board[node].change_color(constants.TILE_SELECT_COLOR)
                self.graphic_board[node].set_select_tex('UI_select_node', self.player_num)

            self.selected_node = node

    def highlight_node(self, node):
        if self.highlighted_node != node:
            if self.highlighted_node is not None and self.highlighted_node != self.selected_node:
                self.graphic_board[self.highlighted_node].change_color(
                    constants.TILE_BASE_COLOR)
                self.graphic_board[self.highlighted_node].set_select_tex('none')

            if node is not None and node != self.selected_node:
                self.graphic_board[node].change_color(constants.TILE_SELECT_COLOR)
                self.graphic_board[node].set_select_tex('UI_highlight_node', self.player_num)

            self.highlighted_node = node

    def highlight_tile(self, tile):
        if self.highlighted_tile != tile:
            if self.highlighted_tile is not None and self.highlighted_tile != self.selected_tile:
                self.graphic_board[self.highlighted_tile].change_color(
                    constants.TILE_BASE_COLOR)

            if tile is not None and tile != self.selected_tile:
                self.graphic_board[tile].change_color(constants.TILE_HIGHLIGHT_COLOR)

            self.highlighted_tile = tile

    def select_card(self, card):
        if self.selected_card != card:
            if self.selected_card is not None:
                if self.highlighted_card is not None and self.highlighted_card == self.selected_card:
                    self.card_holder.select_card(self.selected_card, False, full=False)
                else:
                    self.card_holder.select_card(self.selected_card, False, full=True)

            if card is not None:
                if self.highlighted_card is not None and self.highlighted_card == card:
                    self.card_holder.select_card(card, True, full=False)
                else:
                    self.card_holder.select_card(card, True, full=True)

            self.selected_card = card

    def highlight_card(self, card):
        if self.highlighted_card != card:
            if self.highlighted_card is not None and self.highlighted_card != self.selected_card:
                self.card_holder.select_card(self.highlighted_card, False)

            if card is not None and card != self.selected_card:
                self.card_holder.select_card(card, True)

            self.highlighted_card = card

    def on_mouse_click(self, x, y):
        if self.initialized:
            if not self.logic.turn_validated[self.player_num]:
                card = self.card_holder.mouse_to_card(x, y)
                self.select_card(card)
                if card is not None:
                    self.select_node(None)
                else:
                    node = self.graphic_board.mouse_to_node_coord(x, y)
                    if node is not None and self.perform(self.player_num, GameAction.CONQUER, node):
                        self.select_node(node)

    def on_mouse_move(self, x, y):
        if self.initialized:

            card = self.card_holder.mouse_to_card(x, y)
            self.highlight_card(card)

            if card is None:
                node = self.graphic_board.mouse_to_node_coord(x, y)
                self.highlight_node(node)

            else:
                self.highlight_node(None)

    def on_mouse_scroll(self, mouse_x, mouse_y, scroll_x, scroll_y):
        if self.initialized:
            self.graphic_board.on_mouse_scroll(mouse_x, mouse_y, scroll_x, scroll_y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.initialized:
            self.graphic_board.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def on_resize(self, width, height):
        self.graphic_board.on_resize(width, height)

    def update(self, dt, move):
        self.graphic_board.update(dt, move)
        self.card_holder.update()

    def draw(self):
        self.graphic_board.draw()
        self.card_holder.draw()

    def load_state(self, state):
        self.logic = state
        for coord, tile in state.logic_tiles_board.items():
            self.graphic_board.tiles[coord].set_object(Game.OBJECTS_DICT['tiles'][tile.type],
                                                       owner=tile.owner)
        for coord, node in state.logic_nodes_board.items():
            self.graphic_board.nodes[coord].set_object(
                Game.OBJECTS_DICT['nodes'][Game.RULES_DICT['board']['node_object']], node.owner)

        self.initialized = True

    def delete(self):
        self.graphic_board.delete()
