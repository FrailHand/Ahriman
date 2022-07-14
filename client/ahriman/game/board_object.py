import math

from .gameTex import *


class BoardObject:
    # layers drawn on the 'ground'
    GROUND_LAYERS = 4

    # layers per texture
    TEXTURE_LAYERS = 3

    # layers drawn before the first tile (ground + 1 row of totems)
    BOTTOM_LAYERS = GROUND_LAYERS + TEXTURE_LAYERS

    @staticmethod
    def owned_texture(texture, owner):
        if owner == -2:
            return 'none'
        elif owner == -1:
            string_owner = 'n'
        else:
            string_owner = str(owner)

        return '_'.join((texture, string_owner)) if texture != 'none' else 'none'

    def __init__(self, batch):

        self.tex_dict = None

        self.batch = batch
        self.color = constants.TILE_BASE_COLOR

        self.texture_managers = {}

    def update(self):
        for manager in self.texture_managers.values():
            manager.update()

    def delete(self):
        for manager in self.texture_managers.values():
            manager.delete()

    def change_color(self, color):
        self.color = color

        for key, manager in self.texture_managers.items():
            if key != 'select' and key != 'symbol':
                manager.change_color(color)

    def set_select_tex(self, tex, player=-1):
        named_tex = BoardObject.owned_texture(tex, player)
        self.texture_managers['select'].change_texture(named_tex)

    def set_object(self, object_dict, owner=-1):
        self.tex_dict = object_dict['textures']

        self.change_owner(owner)

    def change_owner(self, owner):
        for key, manager in self.texture_managers.items():
            texture = 'none'
            if key in self.tex_dict:
                texture = self.tex_dict[key]

            manager.change_texture(Tile.owned_texture(texture, owner))


class Tile(BoardObject):
    """entity rendering one tile of the board"""

    # layers per tile
    TILE_LAYERS = 3 * BoardObject.TEXTURE_LAYERS + 1

    MID_COORDS = 0.5
    BACK_COORDS = 0.3
    FRONT_COORDS = 0.7

    SYMBOL_HEIGHT = 0

    def __init__(self, batch, hx, hy):
        super().__init__(batch)

        x = (hx - constants.BOARD_X_Y_SLOPE * hy) * constants.BOARD_X_STRIDE
        z = constants.BOARD_Y_STRIDE * hy

        select_coords = ('v3f', (
            x, 0, z + 1,
            x + 1, 0, z + 1,
            x + 1, 0, z,
            x, 0, z))
        self.texture_managers['select'] = TextureManager('none', select_coords, self.batch,
                                                         order=1, color4f=self.color)

        bottom_coords = ('v3f', (x, 0, z + 1,
                                 x + 1, 0, z + 1,
                                 x + 1, 0, z,
                                 x, 0, z))
        self.texture_managers['bottom'] = TextureManager('none', bottom_coords, self.batch,
                                                         order=0, color4f=self.color)

        back_coords = ('v3f', (
            x, 0, z + Tile.BACK_COORDS,
            x + 1, 0, z + Tile.BACK_COORDS,
            x + 1, 1, z + Tile.BACK_COORDS,
            x, 1, z + Tile.BACK_COORDS))
        self.texture_managers['back'] = TextureManager('none', back_coords, self.batch,
                                                       Tile.TILE_LAYERS * hy
                                                       + BoardObject.BOTTOM_LAYERS,
                                                       self.color)

        mid_coords = ('v3f', (
            x, 0, z + Tile.MID_COORDS,
            x + 1, 0, z + Tile.MID_COORDS,
            x + 1, 1, z + Tile.MID_COORDS,
            x, 1, z + Tile.MID_COORDS))
        self.texture_managers['mid'] = TextureManager('none', mid_coords, self.batch,
                                                      Tile.TILE_LAYERS * hy
                                                      + BoardObject.TEXTURE_LAYERS
                                                      + BoardObject.BOTTOM_LAYERS,
                                                      self.color)

        front_coords = ('v3f', (
            x, 0, z + Tile.FRONT_COORDS,
            x + 1, 0, z + Tile.FRONT_COORDS,
            x + 1, 1, z + Tile.FRONT_COORDS,
            x, 1, z + Tile.FRONT_COORDS))
        self.texture_managers['front'] = TextureManager('none', front_coords, self.batch,
                                                        Tile.TILE_LAYERS * hy
                                                        + 2 * BoardObject.TEXTURE_LAYERS
                                                        + BoardObject.BOTTOM_LAYERS,
                                                        self.color)

        rad_angle = math.radians(constants.CAMERA_ANGLE)
        dy = 0.5 * math.cos(rad_angle)
        dz = 0.5 * math.sin(rad_angle)

        h = Tile.SYMBOL_HEIGHT + dy

        symbol_coords = ('v3f', (
            x, h - dy, z + Tile.FRONT_COORDS + dz,
            x + 1, h - dy, z + Tile.FRONT_COORDS + dz,
            x + 1, h + dy, z + Tile.FRONT_COORDS - dz,
            x, h + dy, z + Tile.FRONT_COORDS - dz,))

        self.texture_managers['symbol'] = TextureManager('none', symbol_coords, self.batch,
                                                         Tile.TILE_LAYERS * hy
                                                         + 3 * BoardObject.TEXTURE_LAYERS
                                                         + BoardObject.BOTTOM_LAYERS,
                                                         (1, 1, 1, 0))

    def toggle_symbol(self, enable):
        if enable:
            color = constants.TILE_BASE_COLOR
        else:
            color = (1, 1, 1, 0)

        self.texture_managers['symbol'].change_color(color)


class Node(BoardObject):
    def __init__(self, batch, hx, hy, upper):
        super().__init__(batch)

        x = (hx - constants.BOARD_X_Y_SLOPE * hy) * constants.BOARD_X_STRIDE
        z = constants.BOARD_Y_STRIDE * hy

        batch_order = (BoardObject.BOTTOM_LAYERS
                       + Tile.TILE_LAYERS * hy
                       - BoardObject.TEXTURE_LAYERS)

        if not upper:
            x -= math.sqrt(3) / 4
            z += 1 / 4
            batch_order += BoardObject.TEXTURE_LAYERS

        select_coords = ('v3f', (
            x, 0, z + 0.5,
            x + 1, 0, z + 0.5,
            x + 1, 0, z - 0.5,
            x, 0, z - 0.5))
        self.texture_managers['select'] = TextureManager('none', select_coords, self.batch,
                                                         order=2, color4f=self.color)

        bottom_coords = ('v3f', (x, 0, z + 0.5,
                                 x + 1, 0, z + 0.5,
                                 x + 1, 0, z - 0.5,
                                 x, 0, z - 0.5))
        self.texture_managers['bottom'] = TextureManager('none', bottom_coords, self.batch,
                                                         order=3, color4f=self.color)

        mid_coords = ('v3f', (x, 0, z,
                              x + 1, 0, z,
                              x + 1, 1, z,
                              x, 1, z))
        self.texture_managers['mid'] = TextureManager('none', mid_coords, self.batch,
                                                      batch_order,
                                                      self.color)
