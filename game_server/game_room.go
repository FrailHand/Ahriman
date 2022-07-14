package main

import (
	"sync"
	"errors"
	pb "franmarelli/ahriman/game_server/server_proto"
	"time"
)

//describes a room and its players
type GameRoom struct {
	size        uint8
	players     []string
	streams     []pb.Game_GameStreamServer
	connected   uint8
	condition   chan int
	mutex       sync.Mutex
	timedOut    bool
	inGame      bool
	expireTimer <- chan time.Time
}

func NewGameRoom(players []string) *GameRoom {
	s := new(GameRoom)
	s.players = players
	s.size = uint8(len(players))
	s.connected = 0
	s.streams = make([]pb.Game_GameStreamServer, s.size)
	for index := range s.streams {
		s.streams[index] = nil
	}
	s.condition = make(chan int)
	s.timedOut = false
	s.inGame = false
	return s
}

//send a message to all players in the room (will fail if not full)
func (s *GameRoom) Broadcast(message *pb.GameMessage, issuer uint32) error {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	if s.connected < s.size {
		return errors.New(" Cannot broadcast on not full room")
	}
	for PNum, st := range s.streams {
		if PNum != int(issuer) {
			if err := st.Send(message); err != nil {
				return err
			}
		}
	}
	return nil
}

//send a message to the available players in the room
func (s *GameRoom) UnsafeCast(
	message *pb.GameMessage, issuer uint32) {

	for PNum, st := range s.streams {
		if PNum != int(issuer) && st != nil {
			st.Send(message)
		}
	}
}

//send a detail message to all players in the room (will fail if not full)
func (s *GameRoom) SendDetail() error {
	if s.connected < s.size {
		return errors.New(" Cannot send detail on not full room")
	}

	players := make([]*pb.PlayerInfo, s.size)
	for num, playID := range s.players {
		players[num] = &pb.PlayerInfo{PlayerNum: uint32(num), PlayerID: playID}
	}

	message := &pb.GameMessage{Payload: &pb.GameMessage_RoomInfo{RoomInfo: &pb.RoomDetail{RoomSize: uint32(s.size), Player: players}}}

	for _, st := range s.streams {
		if err := st.Send(message); err != nil {
			return err
		}
	}
	return nil
}
