from math import sin, cos, radians, tan, atan, degrees, floor, sqrt, acos

import pyglet
from pyglet.gl import *
from pyglet.window import key

from ahriman import constants
from .board_object import Tile, Node


class Board:
    """game board containing the tiles"""
    NODE_SELECT_MIN_DIST = 0.25
    NODE_SELECT_ANGLE_MARGIN = 7.5

    FIELD_OF_VIEW = 30

    def __init__(self, window, rows=5, cols=5, mouse_move_hover=False):
        """create hexagonal grid of tiles"""
        glClearColor(*constants.BOARD_BACKGROUND_COLOR)

        self.win = window
        self.batch = pyglet.graphics.Batch()
        self.minx = (-constants.BOARD_X_Y_SLOPE * rows + 1) * constants.BOARD_X_STRIDE
        self.max_x = (cols + constants.BOARD_X_Y_SLOPE * rows - 1) * constants.BOARD_X_STRIDE
        self.min_z = 0.5
        self.max_z = constants.BOARD_Y_STRIDE * (2 * rows - 1) - 0.5

        self.mouse_motion_hover = mouse_move_hover

        self.highlighted = None
        self.selected = None

        self.tiles = {}
        self.nodes = {}

        for hy in range(rows):
            for hx in range(cols + hy):
                self.create_tile(hx, hy)
        for hy in range(rows, 2 * rows - 1):
            for hx in range(hy - rows + 1, cols + rows - 1):
                self.create_tile(hx, hy)

        self.project = Projector(self.win.width, self.win.height,
                                 ((self.max_x + self.minx) / 2, 0, (self.max_z + self.min_z) / 2),
                                 constants.CAMERA_ANGLE, ((self.minx, self.max_x), (3, 10), (self.min_z, self.max_z)),
                                 fov=Board.FIELD_OF_VIEW)

        self.rows = rows
        self.cols = cols

    def __setitem__(self, coord, value):
        if len(coord) == 2:
            self.tiles[coord] = value
        elif len(coord) == 3:
            self.nodes[coord] = value
        else:
            raise (ValueError('invalid key length: {}'.format(len(coord))))

    def __getitem__(self, coord):
        if len(coord) == 2:
            return self.tiles[coord]
        elif len(coord) == 3:
            return self.nodes[coord]
        else:
            raise (ValueError('invalid key length: {}'.format(len(coord))))

    def create_tile(self, hx, hy):
        self.tiles[(hx, hy)] = Tile(self.batch, hx, hy)
        self.nodes[(hx, hy, 0)] = Node(self.batch, hx, hy, 0)
        self.nodes[(hx, hy, 1)] = Node(self.batch, hx, hy, 1)

        self.nodes[(hx + 1, hy + 1, 0)] = Node(self.batch, hx + 1, hy + 1, 0)
        self.nodes[(hx + 1, hy + 1, 1)] = Node(self.batch, hx + 1, hy + 1, 1)

        self.nodes[(hx + 1, hy, 0)] = Node(self.batch, hx + 1, hy, 0)
        self.nodes[(hx, hy + 1, 1)] = Node(self.batch, hx, hy + 1, 1)

    def update(self, dt, move=True):
        if move:
            self.move_cam(dt)
        for tile in self.tiles.values():
            tile.update()
        for node in self.nodes.values():
            node.update()

    def toggle_symbols(self, enable):
        for tile in self.tiles.values():
            tile.toggle_symbol(enable)

    def delete(self):
        for tile in self.tiles.values():
            tile.delete()
        for node in self.nodes.values():
            node.delete()

    def draw(self):
        glPushMatrix()
        self.project.perspective()
        self.batch.draw()
        glPopMatrix()

    def mouse_to_board_coord(self, x, y):
        (vx, vy) = self.project.get_virtual(x, y)
        hyf = vy / constants.BOARD_Y_STRIDE
        hxf = (vx / constants.BOARD_X_STRIDE) + constants.BOARD_X_Y_SLOPE * floor(hyf) - (
                1 - constants.BOARD_X_STRIDE) / 2

        return hxf, hyf

    def mouse_to_tile_coord(self, x, y):
        hxf, hyf = self.mouse_to_board_coord(x, y)

        if hyf % 1 < 0.5:
            hyf2 = hyf - abs(hxf % 1 - 0.5) * sqrt(3) / 3
            if floor(hyf2) != floor(hyf):
                hxf -= constants.BOARD_X_Y_SLOPE
                hyf = hyf2

        hy = floor(hyf)
        hx = floor(hxf)

        if (hx, hy) in self.tiles:
            return hx, hy

        return None

    def mouse_to_node_coord(self, x, y):
        hxf, hyf = self.mouse_to_board_coord(x, y)
        fx, fy = floor(hxf), floor(hyf)

        trigo_x = (hxf % 1) * sqrt(3) / 2 - sqrt(3) / 4
        trigo_y = (hyf % 1) * 0.75 - 0.5
        vector_norm = sqrt(trigo_x ** 2 + trigo_y ** 2)
        if vector_norm < Board.NODE_SELECT_MIN_DIST:
            return None

        cosine = trigo_x / vector_norm
        angle = degrees(acos(cosine))

        if Board.NODE_SELECT_ANGLE_MARGIN < angle < 60 - Board.NODE_SELECT_ANGLE_MARGIN:
            if trigo_y > 0:
                node = (fx + 1, fy + 1, 1)
            else:
                node = (fx + 1, fy, 0)
        elif 60 + Board.NODE_SELECT_ANGLE_MARGIN < angle < 120 - Board.NODE_SELECT_ANGLE_MARGIN:
            if trigo_y > 0:
                node = (fx + 1, fy + 1, 0)
            else:
                node = (fx, fy, 1)
        elif 120 + Board.NODE_SELECT_ANGLE_MARGIN < angle < 180 - Board.NODE_SELECT_ANGLE_MARGIN:
            if trigo_y > 0:
                node = (fx, fy + 1, 1)
            else:
                node = (fx, fy, 0)
        else:
            return None

        if node in self.nodes:
            return node
        return None

    def move_cam(self, dt):
        if not self.win.mouse_dragging:
            move_x = 0
            move_z = 0
            zoom = 0

            if self.win.keys[key.UP]:
                move_z -= 0.1

            if self.win.keys[key.DOWN]:
                move_z += 0.1

            if self.win.keys[key.LEFT]:
                move_x -= 0.1

            if self.win.keys[key.RIGHT]:
                move_x += 0.1

            if self.win.keys[key.NUM_ADD]:
                zoom += 0.5

            if self.win.keys[key.NUM_SUBTRACT]:
                zoom -= 0.5

            if self.mouse_motion_hover:
                if self.win.mouse[1] > int(0.9 * self.win.height) and self.win.mouse_in:
                    move_z = - ((self.win.mouse[1] / self.win.height) - 0.9) ** 2 / 0.1

                elif self.win.mouse[1] < int(0.1 * self.win.height) and self.win.mouse_in:
                    move_z = ((self.win.mouse[1] / self.win.height) - 0.1) ** 2 / 0.1

                if self.win.mouse[0] < int(0.1 * self.win.width) and self.win.mouse_in:
                    move_x = - ((self.win.mouse[0] / self.win.width) - 0.1) ** 2 / 0.1

                elif self.win.mouse[0] > int(0.9 * self.win.width) and self.win.mouse_in:
                    move_x = ((self.win.mouse[0] / self.win.width) - 0.9) ** 2 / 0.1

            self.project.cam.move(move_x * dt * constants.WIN_UPDATE_RATE,
                                  move_z * dt * constants.WIN_UPDATE_RATE, zoom)

    def on_resize(self, w, h):
        self.project.on_resize(w, h)

    def on_mouse_scroll(self, mouse_x, mouse_y, scroll_x, scroll_y):
        vx, vy = self.project.get_virtual(mouse_x, mouse_y)
        self.project.cam.move(0, 0, scroll_y, zoom_point=(vx, vy))

    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        last_x = x - dx
        last_y = y - dy
        lvx, lvy = self.project.get_virtual(last_x, last_y)
        vx, vy = self.project.get_virtual(x, y)
        dvx = lvx - vx
        dvy = lvy - vy
        self.project.cam.move(dvx, dvy, 0)


class Projector:
    """perspective projection camera with inverse projection computation"""

    def __init__(self, width, height, focus, angle, boundaries, distance=10, fov=60):
        self.fov = radians(fov)
        self.ratio = width / height
        self.width = width / 2
        self.height = height / 2
        self.cam = SimpleCam(focus, angle, boundaries, distance)

        self.tanthet = tan(self.fov / 2)
        self.cotgam = 1 / tan(self.cam.angle)
        self.cosgam = cos(self.cam.angle)

        self.R = self.height * sin(self.fov / 2 + self.cam.angle) / sin(self.fov / 2)

    def on_resize(self, width, height):
        self.ratio = width / height
        self.width = width / 2
        self.height = height / 2

        self.R = self.height * sin(self.fov / 2 + self.cam.angle) / sin(self.fov / 2)

    def perspective(self):
        """generate the perspective rendering"""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(degrees(self.fov), self.ratio, 0.05, 1000)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        self.cam.perspective()

    def get_virtual(self, x, y):
        """get the coordinates of the mouse in the projected ground plane"""
        alpha = - atan(((y / self.height) - 1) * self.tanthet)
        yv = (self.cam.lz - self.cam.y * ((1 / tan(alpha + self.cam.angle)) - self.cotgam))

        yp = y * self.cosgam
        xv = (self.cam.lx + self.cam.y * (x - self.width) / (self.R - yp))

        return xv, yv


class SimpleCam:
    """camera with fixed orientation and limited moving area"""

    def __init__(self, focus, angle, boundaries, distance):
        self.angle = radians(angle)
        self.lx = focus[0]
        self.ly = focus[1]
        self.lz = focus[2]
        self.x = self.lx
        self.y = self.ly + sin(self.angle) * distance
        self.z = self.lz + cos(self.angle) * distance
        self.x_lim = boundaries[0]
        self.y_lim = boundaries[1]
        self.z_lim = boundaries[2]

    def perspective(self):
        """place camera in space"""
        gluLookAt(self.x, self.y, self.z, self.lx, self.ly, self.lz, 0, 1, 0)

    def move(self, dx, dz, zoom, zoom_point=None):
        dy = - 0.4 * zoom * sin(self.angle)

        if self.y_lim[0] < (self.y + dy) < self.y_lim[1]:
            # TODO change this line for fantastic zoom
            # but do not forget to calculate self.angle after that
            dy_dz = dy * (self.lz - self.z) / self.y
            self.z -= dy_dz

            self.y += dy

            if zoom_point is not None:
                dx += (self.x - zoom_point[0]) * dy / (self.y - dy)
                dz += (self.lz - zoom_point[1]) * dy / (self.y - dy)

        if self.z_lim[0] < (self.lz + dz) < self.z_lim[1]:
            self.lz += dz
            self.z += dz

        if self.x_lim[0] < (self.lx + dx) < self.x_lim[1]:
            self.lx += dx
            self.x += dx
