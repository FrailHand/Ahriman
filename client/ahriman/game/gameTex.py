from builtins import FileNotFoundError
from itertools import compress
from math import floor
from time import time

import json
import pyglet
import re
from os import listdir
from os import path
from pyglet.gl import *
from random import randint
from threading import Condition

from ahriman import constants
from ahriman import logger

DEFAULT_FRAMERATE = 6


class GameTex:
    """animated texture with multiple frames played at regular interval"""

    @staticmethod
    def get_tex(file):
        """load a texture with no blur filter on resize (pixel art)"""
        tex = pyglet.image.load(file).texture
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        return tex

    def __init__(self, texture_name, frames_list, framerate=DEFAULT_FRAMERATE):
        self.frames_list = frames_list
        self.frame_rate = framerate

        texture_dirs = listdir(path.join(constants.RESOURCE_PATH, 'textures', texture_name))
        if len(texture_dirs) == 0:
            logger.warning('empty resource directory :', texture_name)
            return

        def natural_key(string):
            return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string)]

        # sort layers by orders to know the number of the last one
        texture_dirs.sort(key=natural_key)

        max_layer = int(texture_dirs[-1][1:].split('_sprite_')[0])

        # create as many layers as detected
        self.layers = []
        for index in range(max_layer + 1):
            self.layers.append([])

        for tex in texture_dirs:
            if tex != 'info':
                layer = int(tex[1:].split('_sprite_')[0])
                file_name = path.join(constants.RESOURCE_PATH, 'textures', texture_name, tex)
                self.layers[layer].append(GameTex.get_tex(file_name))

        check_length = len(self.layers[0])
        for layer in self.layers[1:]:
            if len(layer) != check_length:
                logger.error('layers must have equal amount of frames - {}'.format(texture_name),
                             title='in loading GameTex')
                raise ValueError('inconsistent layer amount')

        # check if frame list is empty
        if not self.frames_list:
            self.frames_list = list(range(check_length))


class AnimTexCounter:
    """entity that counts the current frame in an animated texture"""

    def __init__(self, texture):
        self.frames = texture.frames_list
        self.freq = texture.frame_rate
        self.index_counter = randint(0, len(self.frames) - 1)
        self.current_time = -1

    @property
    def counter(self):
        return self.frames[self.index_counter]

    def update(self):
        if self.current_time == -1:
            self.current_time = floor(time() * self.freq)
            return True
        elif len(self.frames) > 1:
            temp = floor(time() * self.freq)
            if temp != self.current_time:
                self.current_time = temp
                self.index_counter = (self.index_counter + 1) % len(self.frames)
                return True


class TextureManager:
    """global texture manager handling texture, animation and rendering"""

    textures = {'none': None}
    textures_loaded = False
    loading_condition = Condition()

    @staticmethod
    def load_textures():
        with TextureManager.loading_condition:
            if TextureManager.textures_loaded:
                return True
            else:
                # automatically load all textures

                logger.info('loading textures...')
                texture_dirs = listdir(path.join(constants.RESOURCE_PATH, 'textures'))
                for tex in texture_dirs:
                    if path.isdir(path.join(constants.RESOURCE_PATH, 'textures', tex)):
                        TextureManager.parse_tex(tex)
                logger.confirm('textures successfully loaded !')

                TextureManager.textures_loaded = True
                TextureManager.loading_condition.notify_all()
                return True

    @staticmethod
    def parse_tex(texture_dir):
        """open a texture directory and load it in memory"""
        contents = listdir(path.join(constants.RESOURCE_PATH, 'textures', texture_dir))
        bool_sub = [path.isdir(path.join(constants.RESOURCE_PATH, 'textures', texture_dir, sub)) for
                    sub in contents]
        is_subdir = any(bool_sub)

        if is_subdir:
            subdirs = list(compress(contents, bool_sub))
            for sub in subdirs:
                TextureManager.parse_tex(path.join(texture_dir, sub))
        else:
            try:
                with open(path.join(constants.RESOURCE_PATH, 'textures', texture_dir, 'info'),
                          'r') as file:
                    try:
                        info = json.load(file)

                        try:
                            frames = info['frames_list']

                            if frames.__class__ is not list:
                                logger.error(texture_dir, title='frames_list must be a list')
                                return

                        except KeyError as e:
                            logger.error(e, title='missing field in texture {} info file'.format(
                                texture_dir))
                            return

                    except Exception as e:
                        logger.error(e, title='in json texture info {}'.format(texture_dir))
                        return

            except FileNotFoundError as e:
                frames = []

            split_path = []
            root = texture_dir
            while root != '':
                root, leaf = path.split(root)
                split_path.append(leaf)

            split_path.reverse()
            texture_name = '_'.join(split_path)

            # noinspection PyTypeChecker
            TextureManager.textures[texture_name] = GameTex(texture_dir, frames)

    def __init__(self, texture_name, coords, batch, order=0, color4f=(1, 1, 1, 1), layer_spacing=0.1):
        with TextureManager.loading_condition:
            loaded = TextureManager.textures_loaded
        if not loaded:
            logger.warning('sub-optimized textures loading')
            TextureManager.load_textures()

        self.texture = TextureManager.textures[texture_name]
        self.vlist = None
        self.coords_type = coords[0]
        self.coords = tuple(coords[1])
        self.move_coords = None
        self.batch = batch
        self.order = order
        self.color = color4f
        self.spacing = layer_spacing
        self.update_next = False

        if self.texture is not None:
            self.anim = AnimTexCounter(self.texture)
        else:
            self.anim = None

    def update(self):
        if self.texture is not None and (self.anim.update() or self.update_next):
            self.update_next = False

            if self.vlist is not None:
                for vertex in self.vlist:
                    vertex.delete()
            self.vlist = []

            if self.move_coords is not None:
                self.coords = self.move_coords
                self.move_coords = None

            centering = (len(self.texture.layers) - 1) / 2

            for num, layer in enumerate(self.texture.layers):
                coord = (self.coords_type, tuple(
                    elmt if (ind + 1) % 3 != 0 else elmt + (num - centering) * self.spacing for
                    ind, elmt in
                    enumerate(self.coords)))

                self.vlist.append(self.batch.add(4, GL_QUADS,
                                                 OCATextureGroup(layer[self.anim.counter],
                                                                 self.order + num, self.color),
                                                 coord, ('t2f', (0, 0, 1, 0, 1, 1, 0, 1))))

        elif self.move_coords is not None:
            if self.move_coords == self.coords:
                self.move_coords = None
            else:
                self.coords = self.move_coords
                self.move_coords = None

                if self.vlist is not None:
                    centering = (len(self.vlist) - 1) / 2

                    for num, vertex in enumerate(self.vlist):
                        coord = tuple(
                            elmt if (ind + 1) % 3 != 0 else elmt + (num - centering) * self.spacing for ind, elmt in
                            enumerate(self.coords))
                        vertex.vertices[:] = coord

    def change_color(self, color):
        self.color = color
        self.update_next = True

    def change_texture(self, texture_name):
        self.texture = TextureManager.textures[texture_name]
        if self.texture is not None:
            self.anim = AnimTexCounter(self.texture)
        else:
            self.anim = None
            if self.vlist is not None:
                for vertex in self.vlist:
                    vertex.delete()
                self.vlist = None

    def delete(self):
        if self.vlist is not None:
            for vertex in self.vlist:
                vertex.delete()

    def move(self, coords):
        self.move_coords = tuple(coords)


class EnableAlphaGroup(pyglet.graphics.OrderedGroup):
    """texture group with transparency but no depth test"""

    def __init__(self, order):
        super().__init__(order)

    def set_state(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)

    def unset_state(self):
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glDisable(GL_CULL_FACE)


class ColorGroup(pyglet.graphics.Group):
    """texture group with transparency and color"""

    def __init__(self, order=0, color4f=(1, 1, 1, 1)):
        self.color = color4f
        bt_tex_en = EnableAlphaGroup(order)
        super().__init__(parent=bt_tex_en)

    def set_state(self):
        glColor4f(*self.color)


class OCATextureGroup(pyglet.graphics.TextureGroup):
    """texture group with transparency, color and order"""

    def __init__(self, texture, order=0, color4f=(1, 1, 1, 1)):
        col_gr = ColorGroup(order, color4f)
        super().__init__(texture, parent=col_gr)
