def main():
    import sys
    import os

    main_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
    sys.path.append(main_dir)

    from ahriman import logger

    import pyglet
    from ahriman.window import Window

    logger.info('launching Client')
    window = Window()

    try:
        pyglet.app.run()
    finally:
        logger.info('shutting down Client')
        window.gameClient.quit()


if __name__ == '__main__':
    main()
