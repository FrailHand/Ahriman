from ahriman.window import Window


class DevWindow(Window):
    def __init__(self):
        super().__init__()
        from ahriman.activities.gameActivity import GameActivity
        from ahriman.game import TextureManager
        TextureManager.load_textures()
        from ahriman.game import Game
        Game.parse_logic()
        self.gameClient.playerNum = 0
        self.activity = GameActivity(self, ['dev'] * 2)


def dev_main():
    import sys
    import os

    main_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
    sys.path.append(main_dir)

    from ahriman import logger

    import pyglet

    logger.info('launching Client')
    window = DevWindow()

    try:
        pyglet.app.run()
    finally:
        logger.info('shutting down Client')
        window.gameClient.quit()


if __name__ == '__main__':
    dev_main()
