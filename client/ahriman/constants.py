import os
from enum import Enum, auto

SOURCE_PATH = os.path.dirname(os.path.realpath(__file__))
RESOURCE_PATH = os.path.join(os.path.dirname(SOURCE_PATH), 'resource')
LOCAL_PATH = os.path.join(os.path.dirname(SOURCE_PATH), 'local')

LOGIC_PATH = os.path.join(RESOURCE_PATH, 'logic')
LOGIC_OBJECTS = os.path.join(LOGIC_PATH, 'objects.json')
LOGIC_RULES = os.path.join(LOGIC_PATH, 'rules.json')

LOGIN_SAVE_FILE = 'keep_login'

# TODO do this someway else ?
if not os.path.exists(LOCAL_PATH):
    os.makedirs(LOCAL_PATH)

INTRO_SCREENS = [os.path.join('backgrounds', 'menu.png')]
INTRO_SCREEN_HOLD = 1
INTRO_SCREEN_SPEED = 1.5

FADING_COLOR = (1, 1, 1)
FADING_SPEED = 2

# Communication parameters
GAME_SERVER = 'legodroid.dynu.net:51017'
AUTH_SERVER = 'legodroid.dynu.net:51018'
CERT_FILE = os.path.join(RESOURCE_PATH, 'certs', 'server.crt')

SPRITE_FRAMERATE = 6

# default window size for non full-screen (best fit with background and GUIs)
DEFAULT_WIN_SIZE = (800, 500)
WIN_UPDATE_RATE = 60

# game queues
DEFAULT_QUEUE = 0

# time before allowing to leave when disconnection
LEAVING_TIMEOUT = 3

# base colors for board
TILE_BASE_COLOR = (1, 1, 1, 1)
TILE_HIGHLIGHT_COLOR = (0.9, 0.9, 0.9, 1)
TILE_SELECT_COLOR = TILE_BASE_COLOR
BOARD_BACKGROUND_COLOR = (0.5, 0.7, 1, 1)

# offsets for tile positioning
BOARD_X_Y_SLOPE = 0.5
BOARD_Y_STRIDE = 0.75
BOARD_X_STRIDE = 0.866
CAMERA_ANGLE = 45

# double-click max delay
MOUSE_DOUBLE_CLICK_DELAY = 0.5
CARD_ANIMATION_DURATION = 0.35

# texture classification
TEXTURE_CLASS = {
    'bottom': 'bottoms',
    'back': 'fronts',
    'mid': 'fronts',
    'front': 'fronts',
}


# game client event queue
class Event(Enum):
    WINDOW_EVENT = auto()
    PLAYER_EVENT = auto()
    SEARCH_EVENT = auto()
    GAME_EVENT = auto()
    AUTH_EVENT = auto()


class WindowEvent(Enum):
    FADE_END = auto(),
    ERROR = auto()


class PlayerEvent(Enum):
    END_TURN = auto()
    SYMBOLS_TOGGLE = auto()


class SearchEvent(Enum):
    ERROR = auto()
    GAME_FOUND = auto()
    CANCELED = auto()
    OUT_OF_ID = auto()
    PENDING_FOUND = auto()


class GameEvent(Enum):
    ACTION = auto()
    CONNECTION = auto()
    ROOM_FULL = auto()
    END_OF_CONNECTION = auto()
    BOARD_STATE = auto()


class AuthEvent(Enum):
    ERROR = auto()
    SUCCESS = auto()
    REFUSED = auto()


class GameAction(Enum):
    TURN_DONE = auto()
    CONQUER = auto()
    RESOLVED = auto()

    def __int__(self):
        return self.value
