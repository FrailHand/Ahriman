import functools

import collections

from ahriman import logger
from ahriman.constants import GameAction


class LogicObject:
    def __init__(self, owner):
        self.owner = owner

    @staticmethod
    def ownership_check(logic_object, owner):
        return logic_object.owner == owner


class LogicTile(LogicObject):
    def __init__(self, tile_type, owner, total_players):
        super().__init__(owner)
        self.type = tile_type
        self.nodes = [0] * total_players

    def update_owner(self, owner, value):
        # add/remove nodes for a player on this tile
        self.nodes[owner] += value
        new_owner = 0
        ex_aequo = False

        for index in range(1, len(self.nodes)):
            if self.nodes[index] == self.nodes[new_owner]:
                ex_aequo = True
            elif self.nodes[index] > self.nodes[new_owner]:
                ex_aequo = False
                new_owner = index

        if ex_aequo:
            new_owner = -1

        self.owner = new_owner


class LogicNode(LogicObject):
    # owner: -2 for empty, -1 for black stone
    def __init__(self, owner):
        super().__init__(owner)


class Logic:
    def __init__(self, total_players=2):
        self.total_players = total_players
        self.logic_tiles_board = {}
        self.logic_nodes_board = {}
        self.turn_validated = [False] * total_players

        self.owned_tiles = [0] * total_players
        self.captures = [0] * total_players
        self.victory_points = [0] * total_players

    def __setitem__(self, coord, value):
        if len(coord) == 2:
            self.logic_tiles_board[coord] = value
        elif len(coord) == 3:
            self.logic_nodes_board[coord] = value
        else:
            raise (ValueError('invalid key length: {}'.format(len(coord))))

    def __getitem__(self, coord):
        if isinstance(coord[0], int):
            if len(coord) == 2:
                return self.logic_tiles_board[coord]
            elif len(coord) == 3:
                return self.logic_nodes_board[coord]
            else:
                raise (ValueError('invalid key length: {}'.format(len(coord))))
        else:
            return [self[item] for item in coord]

    def add_node(self, coord, owner):
        self.logic_nodes_board[coord] = LogicNode(owner)

    def add_tile(self, tile_coord, tile_name, owner):
        self.logic_tiles_board[tile_coord] = LogicTile(tile_name, owner, self.total_players)

    def adjacent_tiles(self, coord):
        if len(coord) == 2:
            increments = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)]
        elif len(coord) == 3:
            increments = [(0, 0), (-1, -1), (0, -1) if coord[2] else (-1, 0)]
        else:
            raise (ValueError('incorrect coordinate length: {} - expected [2, 3]'.format(len(coord))))

        return [(coord[0] + dx, coord[1] + dy) for dx, dy in increments if
                ((coord[0] + dx, coord[1] + dy) in self.logic_tiles_board)]

    def adjacent_nodes(self, node_coord):
        up = int(not node_coord[2])
        increments = [(0, 0), (1, 0), (0, -1)]
        if up:
            increments = [(-dx, -dy) for (dx, dy) in increments]

        return [(node_coord[0] + dx, node_coord[1] + dy, up) for dx, dy in increments if
                ((node_coord[0] + dx, node_coord[1] + dy, up) in self.logic_nodes_board)]

    def can_perform(self, player, action, coord):
        if action == GameAction.CONQUER:
            if len(coord) != 3:
                return False
            if self.logic_nodes_board[coord].owner != -2:
                return False
            if self.owned_tiles[player] == 0:
                return True

            owner_check = functools.partial(LogicObject.ownership_check, owner=player)
            adjacent = self[self.adjacent_tiles(coord)]
            ownership = map(owner_check, adjacent)
            return any(ownership)

        raise (TypeError('unknown action: {}'.format(action)))

    def change_node_owner(self, node, new_owner):
        old_owner = self.logic_nodes_board[node].owner
        self.logic_nodes_board[node].owner = new_owner
        to_update = set()
        to_update.add(node)

        for tile_coord in self.adjacent_tiles(node):
            tile = self.logic_tiles_board[tile_coord]
            old_tile_owner = tile.owner

            if new_owner >= 0:
                tile.update_owner(new_owner, 1)

            if old_owner >= 0:
                tile.update_owner(old_owner, -1)

            if old_tile_owner != tile.owner:
                to_update.add(tile_coord)
                if old_tile_owner >= 0:
                    self.owned_tiles[old_tile_owner] -= 1
                if tile.owner >= 0:
                    self.owned_tiles[tile.owner] += 1

        return to_update

    def resolve(self, actions):
        to_update = set()
        check_capture = set()
        for player, action_tuple in enumerate(actions):
            action, coord = action_tuple

            if action == GameAction.RESOLVED:
                # action has already been resolved during this turn
                pass

            elif action == GameAction.CONQUER:
                conflict = False
                for index in range(player + 1, len(actions)):
                    if actions[index] == action_tuple:
                        actions[index] = (GameAction.RESOLVED, actions[index][1])
                        conflict = True
                if conflict:
                    self.logic_nodes_board[coord].owner = -1
                    to_update.add(coord)
                else:
                    to_update |= self.change_node_owner(coord, player)
                    check_capture.add(coord)
                    check_capture |= set(self.adjacent_nodes(coord))

            else:
                logger.error('unrecognized action - {}'.format(action), 'in Logic.resolve')

        to_capture = set()
        for node in check_capture:
            if self[node].owner < 0:
                continue

            adjacent_nodes = [node_object.owner for node_object in self[self.adjacent_nodes(node)] if
                              node_object.owner >= 0 and node_object.owner != self[node].owner]

            count = collections.Counter(adjacent_nodes)
            if len(count) > 0:
                player = max(count, key=count.get)
                if count[player] >= 2:
                    to_capture.add(node)
                    self.captures[player] += 1

        for node in to_capture:
            to_update |= self.change_node_owner(node, -2)

        self.victory_points = [self.captures[player] + self.owned_tiles[player] for player in
                               range(len(self.victory_points))]

        self.turn_validated = [False] * self.total_players
        return to_update
