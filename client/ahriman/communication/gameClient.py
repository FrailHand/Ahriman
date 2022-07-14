import queue
import threading

from ahriman import constants
from ahriman import logger
from .grpc_proto.server_proto_pb2 import *
from .grpc_proto.server_proto_pb2_grpc import *


class GameClient:
    """
    communication client that will connect to the game server and send info
    also remembers the state (game room, player token, etc.)
    """

    def __init__(self, window):
        self.window = window
        # load the certification file for authenticated communication
        with open(constants.CERT_FILE, 'rb') as cert_file:
            root_certs = cert_file.read()

        credentials = grpc.ssl_channel_credentials(
            root_certificates=root_certs)
        channel = grpc.secure_channel(constants.GAME_SERVER, credentials)
        self.gameStub = GameStub(channel)

        # message sending queue for room request
        self.rr_queue = StubQueue()

        # message sending queue for game stream
        self.gs_queue = StubQueue()

        self.token = ''
        self.roomID = -1
        self.playerNum = -1

    def authenticate(self, user_id, password, remember):
        """
        connect to the authentication server providing credentials
        triggers constants.AuthEvent on success or failure
        :param user_id: 
        :param password:
        :param remember: 
        """
        with open(constants.CERT_FILE, 'rb') as cert_file:
            root_certs = cert_file.read()
        credentials = grpc.ssl_channel_credentials(
            root_certificates=root_certs)
        channel = grpc.secure_channel(constants.AUTH_SERVER, credentials)
        auth_stub = AuthStub(channel)
        try:
            response = auth_stub.Authentication(
                AuthRequest(user_id=user_id, password=password, remember=remember))

            if response.WhichOneof('response') == 'payload':
                self.token = response.payload.token
                self.window.fire_event((
                    constants.Event.AUTH_EVENT, constants.AuthEvent.SUCCESS, response.payload.code))
            else:
                self.window.fire_event((constants.Event.AUTH_EVENT, constants.AuthEvent.REFUSED))

        except Exception as e:
            logger.warning(e, title='in AuthClient.authenticate')
            self.window.fire_event((constants.Event.AUTH_EVENT, constants.AuthEvent.ERROR))

    def check_pending_game(self):
        """
        ask the game server if the player is already in a running game
        :return: constants.SearchEvent (not fired)
        """
        metadata = [(b'token', self.token)]
        event = constants.SearchEvent.ERROR
        try:
            response = self.gameStub.RoomCheck(RoomRequestMessage(cancel=False), metadata=metadata)
            if response.WhichOneof('response') == 'info':
                self.roomID = response.info.roomID
                self.playerNum = response.info.playerNum
                event = constants.SearchEvent.PENDING_FOUND
            else:
                event = constants.SearchEvent.CANCELED

        except Exception as e:
            logger.warning(e, title='in GameClient.check_pending_game')

        finally:
            return event

    def start_game(self):
        """
        start the thread handling the game
        :return: the thread
        """
        thread = threading.Thread(target=self.run_game)
        thread.start()
        return thread

    def search_game(self, game_mode):
        """
        start the thread to search for a new game
        :param game_mode: the queue to apply for
        :return: the thread
        """
        thread = threading.Thread(target=self.request_game, args=(game_mode,))
        thread.start()
        return thread

    def request_game(self, game_mode):
        """
        search for a current pending game
        if none, asks for a new game
        fires constants.SearchEvent on success or failure
        :param game_mode:
        """
        pg_event = self.check_pending_game()

        # this means no pending game was found, start a new request
        if pg_event == constants.SearchEvent.CANCELED:
            metadata = [(b'token', self.token), (b'roomtype', str(game_mode))]
            self.rr_queue.reset()
            event = constants.SearchEvent.ERROR
            response = self.gameStub.RoomRequest(self.rr_queue.read(), metadata=metadata)

            try:
                for payload in response:
                    response_type = payload.WhichOneof('response')
                    if response_type == 'info':
                        event = constants.SearchEvent.GAME_FOUND
                        self.roomID = payload.info.roomID
                        self.playerNum = payload.info.playerNum
                    elif response_type == 'available':
                        event = constants.SearchEvent.OUT_OF_ID
                    else:
                        logger.warning(response_type, title='invalid field in roomResponse')

                    self.rr_queue.stop()

                if event == constants.SearchEvent.ERROR:
                    event = constants.SearchEvent.CANCELED

            except Exception as e:
                logger.warning(e, title='in GameClient.search_game')

            finally:
                self.rr_queue.stop()
                self.window.fire_event((constants.Event.SEARCH_EVENT, event))
        else:
            self.window.fire_event((constants.Event.SEARCH_EVENT, pg_event))

    def cancel_search(self):
        """
        cancel room request (will eventually trigger a constants.SearchEvent.CANCELED)
        """
        self.rr_queue.put(RoomRequestMessage(cancel=True))

    def run_game(self):
        """
        the function called by the game handling thread
        communicates with the window through constants.GameEvent
        """
        self.gs_queue.reset()

        # establish a connection with the server
        metadata = [(b'token', self.token), (b'roomid', str(self.roomID)),
                    (b'playernum', str(self.playerNum))]
        response = self.gameStub.GameStream(self.gs_queue.read(), metadata=metadata)

        try:
            for message in response:
                one_of = message.WhichOneof('payload')

                if one_of == 'action':
                    sub_one_of = message.action.WhichOneof('coordinate')
                    if sub_one_of == 'tilePos':
                        self.window.fire_event(
                            (constants.Event.GAME_EVENT, constants.GameEvent.ACTION,
                             constants.GameAction(message.action.action),
                             message.action.issuer, (
                                 message.action.tilePos.horizontal,
                                 message.action.tilePos.vertical)))
                    else:
                        self.window.fire_event(
                            (constants.Event.GAME_EVENT, constants.GameEvent.ACTION,
                             constants.GameAction(message.action.action),
                             message.action.issuer, (
                                 message.action.nodePos.horizontal,
                                 message.action.nodePos.vertical,
                                 int(message.action.nodePos.upper))))

                elif one_of == 'connectionInfo':
                    self.window.fire_event((
                        constants.Event.GAME_EVENT, constants.GameEvent.CONNECTION,
                        message.connectionInfo))
                elif one_of == 'roomInfo':
                    self.window.fire_event((
                        constants.Event.GAME_EVENT, constants.GameEvent.ROOM_FULL,
                        message.roomInfo))
                elif one_of == 'boardState':
                    self.window.fire_event((
                        constants.Event.GAME_EVENT, constants.GameEvent.BOARD_STATE,
                        message.boardState))
                else:
                    logger.warning(one_of, title='invalid field in gameMessage')

            self.window.fire_event(
                (constants.Event.GAME_EVENT, constants.GameEvent.END_OF_CONNECTION))

        except Exception as e:
            logger.error(e, title='in GameClient.run_game')
            self.window.fire_event((constants.Event.WINDOW_EVENT, constants.WindowEvent.ERROR, str(e)), priority=True)

        finally:
            self.gs_queue.stop()

    def quit(self):
        """
        close all connections with the servers
        """
        self.rr_queue.stop()
        self.gs_queue.stop()

    def send_game_state(self, byte_state):
        """
        send the complete board state to the game server
        :param byte_state:
        """
        board_bytes = BoardBytes(state=byte_state, issuer=self.playerNum)
        message = GameMessage(boardState=board_bytes)
        self.gs_queue.put(message)

    def send_game_action(self, action, coord=(0, 0)):
        """
        send a game action to the server
        :param action:
        :param coord:
        """

        if len(coord) == 2:
            coordinates = TileCoord(horizontal=coord[0], vertical=coord[1])
            action_message = GameAction(tilePos=coordinates, action=int(action), issuer=self.playerNum)

        elif len(coord) == 3:
            coordinates = NodeCoord(horizontal=coord[0], vertical=coord[1], upper=coord[2])
            action_message = GameAction(nodePos=coordinates, action=int(action), issuer=self.playerNum)

        else:
            raise (ValueError('invalid coordinate length: {} - expected [2, 3]'.format(len(coord))))

        message = GameMessage(action=action_message)
        self.gs_queue.put(message)


class StubQueue(queue.Queue):
    """
    implements a sending queue for the stubs
    this is just a conventional queue with yield enhancement and reset ability
    """

    def read(self):
        while True:
            message = self.get()
            if message is None:
                break
            yield message

    def reset(self):
        with self.mutex:
            self.queue.clear()

    def stop(self):
        self.put(None)
