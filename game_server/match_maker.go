package main

import (
	"container/list"
	"errors"
	"fmt"
	"os"
	"sync"
	"time"

	pb "franmarelli/ahriman/game_server/server_proto"
	"math"
)

const (
	GAME_MODES                = 1 //amount of different modes
	DEFAULT_QUEUE             = 0 //number of the default queue
	VOID_QUEUE_SLEEP_TIME_SEC = 1 //sleep time fot the def queue
	STAT_SLEEP_TIME_SEC       = 1 //sleep time between two log intervals
	LOG_FILE				  = "/tmp/ahriman_game_status"
)

//describes the ID of a player in a room
type PlayerInfo struct {
	roomID    uint32
	playerNum uint32
}

//handles match requests and holds a list of current games
type MatchMaker struct {
	rooms         map[uint32]*GameRoom
	inGamePlayers map[string]PlayerInfo
	currentRoomID uint32

	gameQueues [GAME_MODES]*list.List
	queueMutex [GAME_MODES]*sync.Mutex
	running    bool
	syncing    chan int
	subthreads int
}

func NewMatchMaker() *MatchMaker {
	s := new(MatchMaker)
	for i := range s.gameQueues {
		s.gameQueues[i] = list.New()
		s.queueMutex[i] = &sync.Mutex{}
	}
	s.running = false
	s.rooms = make(map[uint32]*GameRoom)
	s.inGamePlayers = make(map[string]PlayerInfo)
	s.currentRoomID = 0
	s.syncing = make(chan int)
	s.subthreads = 0

	return s
}

func (s *MatchMaker) Launch() {
	s.running = true
	Info("starting MatchMaker")
	go s.run()
	go s.runStat()
}

func (s *MatchMaker) Stop() chan int {
	s.running = false
	Info("shutting down MatchMaker")
	return s.syncing
}

//to be called when a waited subthread ends
func (s *MatchMaker) Sync() {
	s.subthreads -= 1
	if s.subthreads == 0 {
		close(s.syncing)
	}
}

//check the queues for possible matches
func (s *MatchMaker) run() {
	s.subthreads += 1
	for s.running {

		//check the default queue
		if s.gameQueues[DEFAULT_QUEUE].Len() >= 2 {
			s.queueMutex[DEFAULT_QUEUE].Lock()
			emP1 := s.gameQueues[DEFAULT_QUEUE].Front()
			emP2 := emP1.Next()
			req1 := s.gameQueues[DEFAULT_QUEUE].Remove(emP1).(*MatchRequest)
			req2 := s.gameQueues[DEFAULT_QUEUE].Remove(emP2).(*MatchRequest)
			s.queueMutex[DEFAULT_QUEUE].Unlock()

			playerSlice := make([]string, 2)
			playerSlice[0] = req1.playerID
			playerSlice[1] = req2.playerID
			roomID, err := s.CreateRoom(playerSlice)

			if err != nil {
				req1.stream.Send(&pb.RoomResponse{
					Response: &pb.RoomResponse_Available{Available: false}})
				req2.stream.Send(&pb.RoomResponse{
					Response: &pb.RoomResponse_Available{Available: false}})
			} else {
				req1.stream.Send(&pb.RoomResponse{
					Response: &pb.RoomResponse_Info{
						Info: &pb.RoomInfo{RoomID: roomID, PlayerNum: 0}}})
				req2.stream.Send(&pb.RoomResponse{
					Response: &pb.RoomResponse_Info{
						Info: &pb.RoomInfo{RoomID: roomID, PlayerNum: 1}}})
			}

		} else {
			time.Sleep(VOID_QUEUE_SLEEP_TIME_SEC * time.Second)
		}
	}

	s.Sync()
}

func (s *MatchMaker) runStat() {
	s.subthreads += 1
	for s.running {
		s.Stat()
		time.Sleep(STAT_SLEEP_TIME_SEC * time.Second)
	}
	s.Stat()
	s.Sync()
}

//create a request and push it into the corresponding queue
func (s *MatchMaker) SearchGame(
	Type uint32, playerID string, stream pb.Game_RoomRequestServer) (
	*list.Element, error) {
	switch Type {
	case DEFAULT_QUEUE:
		req := NewMatchRequest(playerID, stream)
		s.queueMutex[DEFAULT_QUEUE].Lock()
		element := s.gameQueues[DEFAULT_QUEUE].PushBack(req)
		s.queueMutex[DEFAULT_QUEUE].Unlock()
		return element, nil
	default:
		Warning("received invalid game type in match request")
		return nil, errors.New("invalid game type in match request")
	}
}

//remove your request from the queue
func (s *MatchMaker) CancelSearch(request *list.Element) {
	s.queueMutex[DEFAULT_QUEUE].Lock()
	s.gameQueues[DEFAULT_QUEUE].Remove(request)
	s.queueMutex[DEFAULT_QUEUE].Unlock()
}

//create a room and update the lists
func (s *MatchMaker) CreateRoom(players []string) (uint32, error) {
	if _, ok := s.rooms[s.currentRoomID]; ok {
		Warning("ran out of free room ID")
		return 0, errors.New("out of free room ID")
	}
	room := NewGameRoom(players)
	currentID := s.currentRoomID
	s.rooms[currentID] = room
	for num, player := range players {
		s.inGamePlayers[player] = PlayerInfo{
			currentID, uint32(num)}
	}
	s.currentRoomID = (s.currentRoomID + 1) % math.MaxUint32
	//launch expiration timer
	room.expireTimer = time.After(roomExpiration)
	//launch timeout counter
	go s.WaitForConnect(currentID, room)

	return currentID, nil
}

//delete a room and update the lists
func (s *MatchMaker) DeleteRoom(roomID uint32, room *GameRoom) {
	for _, player := range room.players {
		delete(s.inGamePlayers, player)
	}
	delete(s.rooms, roomID)
}

//identifies a request for a match and the stream of the player asking
type MatchRequest struct {
	stream   pb.Game_RoomRequestServer
	playerID string
}

func NewMatchRequest(
	playerID string, stream pb.Game_RoomRequestServer) *MatchRequest {
	s := new(MatchRequest)
	s.playerID = playerID
	s.stream = stream
	return s
}

//connect a player to a room, send message and wait for the others or timeout
func (s *MatchMaker) Connect(roomID uint32, room *GameRoom, playerNum uint32,
	stream pb.Game_GameStreamServer) error {

	room.mutex.Lock()
	room.streams[playerNum] = stream

	if room.timedOut == true {
		room.mutex.Unlock()
		return errors.New("connection timed out")
	}

	room.connected++

	room.UnsafeCast(&pb.GameMessage{
		Payload: &pb.GameMessage_ConnectionInfo{
			ConnectionInfo: &pb.ConnectionMessage{
				Connection: true, Player: &pb.PlayerInfo{PlayerNum: playerNum,
					PlayerID: room.players[playerNum]}}}}, playerNum)

	if !room.inGame {
		if room.connected < room.size {
			room.mutex.Unlock()
			<-room.condition
			if room.timedOut == false {
				return nil
			} else {
				s.Disconnect(roomID, room, playerNum)
				return errors.New("connection timed out")
			}
		} else {
			close(room.condition)
			room.SendDetail()
			room.inGame = true
			room.mutex.Unlock()
			room.condition = make(chan int)
			return nil
		}
	}

	if room.connected >= room.size {
		room.SendDetail()
	}

	room.mutex.Unlock()
	return nil
}

//disconnect a player from a room, and inform the others
func (s *MatchMaker) Disconnect(roomID uint32, room *GameRoom, playerNum uint32) {
	room.mutex.Lock()
	defer room.mutex.Unlock()

	room.connected--
	if room.connected == 0 {
		s.DeleteRoom(roomID, room)
	} else {
		room.streams[playerNum] = nil
		room.UnsafeCast(&pb.GameMessage{
			Payload: &pb.GameMessage_ConnectionInfo{
				ConnectionInfo: &pb.ConnectionMessage{
					Player: &pb.PlayerInfo{PlayerNum: playerNum, PlayerID: room.players[playerNum]}}}}, playerNum)
	}
}

//wait for players to be connected, return timeout after fixed time if fail
func (s *MatchMaker) WaitForConnect(roomID uint32, room *GameRoom) {
	select {
	case <-room.condition:
		return

	case <-time.After(connectionTimeout):
		room.mutex.Lock()
		defer room.mutex.Unlock()

		if room.connected < room.size {
			if room.connected == 0 {
				s.DeleteRoom(roomID, room)
			}
			room.timedOut = true
			close(room.condition)
			Warning("room %v timed out", roomID)
			return
		} else {
			return
		}
	}
}

func (s *MatchMaker) Stat() {
	f, err := os.Create(LOG_FILE)
	if err != nil {
		panic(err)
	}
	defer f.Close()
	separator := "-------------------------------\n"

	message := separator + "|    Ahriman server status    |\n" + separator
	on_off := ""
	if s.running {
		on_off = "ON"
	} else {
		on_off = "OFF"
	}
	message += fmt.Sprintf("| Service            : %6v |\n", on_off)
	message += separator
	message += fmt.Sprintf("| In game players    : %6v |\n", len(s.inGamePlayers))
	message += fmt.Sprintf("| Active rooms       : %6v |\n", len(s.rooms))
	message += fmt.Sprintf("| Current room ID    : %6v |\n", s.currentRoomID)
	message += separator
	message += fmt.Sprintf("| Awaiting requests  : %6v |\n", s.gameQueues[DEFAULT_QUEUE].Len())
	message += separator
	f.WriteString(message)
}
