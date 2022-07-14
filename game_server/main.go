package main

import (
	"io"
	"net"
	"time"
	"errors"
	"strconv"

	"google.golang.org/grpc"

	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/grpclog"
	"golang.org/x/net/context"

	pb "franmarelli/ahriman/game_server/server_proto"
	"os"
	"os/signal"
	"path/filepath"
	"path"
)

const (
	certPath          = "../certs/server.crt"
	keyPath           = "../certs/server.key"
	port              = ":51017"
	connectionTimeout = time.Second * 10
	roomExpiration    = time.Hour * 5
	secretPath        = "../certs/secret"
)

var (
	basePath   = filepath.Dir(os.Args[0])
	certFile   = path.Join(basePath, certPath)
	keyFile    = path.Join(basePath, keyPath)
	secretFile = path.Join(basePath, secretPath)
)

type GameServer struct {
	matchmaker *MatchMaker
	arbiter    *JWT_arbiter
}

type MessageStruct struct {
	message   *pb.GameMessage
	errorCode error
}

//init the server
func newServer() *GameServer {
	s := new(GameServer)
	s.matchmaker = NewMatchMaker()
	s.matchmaker.Launch()
	s.arbiter = NewArbiter()

	return s
}

//answer to gamestream request (in-game communication handler)
/* steps:
-authenticate
-connect
-forward messages
-disconnect
*/
func (s *GameServer) GameStream(
	stream pb.Game_GameStreamServer) error {

	headers, playerID, err := s.arbiter.Authenticate(stream.Context())
	if err != nil {
		return err
	}

	roomIDmeta, err := ReadHeader(headers, "roomid")
	if err != nil {
		return err
	}
	roomID64, err := strconv.ParseUint(roomIDmeta, 10, 32)
	if err != nil {
		Warning("non uint roomID - %v", playerID)
		return errors.New("Invalid roomID : must be uint")
	}
	roomID := uint32(roomID64)

	playerNumMeta, err := ReadHeader(headers, "playernum")
	if err != nil {
		return err
	}
	playerNum64, err := strconv.ParseUint(playerNumMeta, 10, 32)
	if err != nil {
		Warning("non uint playerNum - %v", playerID)
		return errors.New("Invalid playerNum : must be uint")
	}
	playerNum := uint32(playerNum64)

	room, ok := s.matchmaker.rooms[roomID]
	if !ok {
		Warning("player requested non existing roomID (%v) - %v",
			roomID, playerID)
		return errors.New("Invalid roomID request")
	}
	if room.players[playerNum] != playerID {
		Warning("player gave invalid playerNum - %v", playerID)
		return errors.New("Invalid playerNum request")
	}
	if room.streams[playerNum] != nil {
		Warning("player tried to connect twice to a game - %v", playerID)
		return errors.New("Already in game")
	}

	err = s.matchmaker.Connect(roomID, room, playerNum, stream)
	if err != nil {
		return err
	}
	defer s.matchmaker.Disconnect(roomID, room, playerNum)

	receiveChannel := make(chan MessageStruct)
	chanRecv := func() {
		incoming, err := stream.Recv()
		receiveChannel <- MessageStruct{incoming, err}
	}

	for {
		go chanRecv()
		select {
		case tuple := <-receiveChannel:
			incoming := tuple.message
			err := tuple.errorCode
			if err == io.EOF {
				return nil
			}
			if err != nil {
				Warning("in GameStream: %v", err)
				return err
			}
			if err := room.Broadcast(incoming, playerNum); err != nil {
				Warning("Room broadcast failed : %v", err)
			}
		case <-room.expireTimer:
			close(room.condition)
			Warning("room %v expired", roomID)
			return errors.New("room expired after timeout")
		case <-room.condition:
			return errors.New("room expired after timeout")
		}
	}
}

//answer to roomrequest (new match request handler)
/* steps:
-authenticate
-create a request
-wait for completion or cancellation
 */
func (s *GameServer) RoomRequest(
	stream pb.Game_RoomRequestServer) error {

	headers, playerID, err := s.arbiter.Authenticate(stream.Context())
	if err != nil {
		return err
	}

	roomTypeMeta, err := ReadHeader(headers, "roomtype")
	if err != nil {
		return err
	}
	roomType64, err := strconv.ParseUint(roomTypeMeta, 10, 32)
	if err != nil {
		Warning("non uint roomType - %v", playerID)
		return errors.New("Invalid roomType : must be uint")
	}
	roomType := uint32(roomType64)

	if _, ok := s.matchmaker.inGamePlayers[playerID]; ok {
		Error("player requested a room while already in a game - %v", playerID)
		return errors.New("Player already in game")
	}

	request, err := s.matchmaker.SearchGame(roomType, playerID, stream)
	if err != nil {
		return err
	}
	defer s.matchmaker.CancelSearch(request)

	for {
		msg, err := stream.Recv()
		if err == io.EOF {
			return nil
		}
		if err != nil {
			return err
		}

		if msg.Cancel == true {
			return nil
		}
	}
}

//respond to roomcheck request (check if a player already belongs to a room)
/* steps:
-authenticate
-check players-rooms list
 */
func (s *GameServer) RoomCheck(
	ctx context.Context, request *pb.RoomRequestMessage) (
	*pb.RoomResponse, error) {

	_, playerID, err := s.arbiter.Authenticate(ctx)
	if err != nil {
		return nil, err
	}

	if info, ok := s.matchmaker.inGamePlayers[playerID]; ok {
		return &pb.RoomResponse{Response: &pb.RoomResponse_Info{
			Info: &pb.RoomInfo{
				RoomID: info.roomID, PlayerNum: info.playerNum}}}, nil
	}

	return &pb.RoomResponse{
		Response: &pb.RoomResponse_Available{Available: false}}, nil

}

//initiates the server with credentials
func main() {
	lis, err := net.Listen("tcp", port)
	if err != nil {
		grpclog.Fatalf(time.Now().UTC().Format(time.RFC3339)+
			" : failed to listen: %v", err)
	}
	var opts []grpc.ServerOption
	creds, err := credentials.NewServerTLSFromFile(certFile, keyFile)
	if err != nil {
		grpclog.Fatalf(time.Now().UTC().Format(
			time.RFC3339)+ " : failed to generate credentials %v", err)
	}
	opts = []grpc.ServerOption{grpc.Creds(creds)}
	grpcServer := grpc.NewServer(opts...)
	server := newServer()
	pb.RegisterGameServer(grpcServer, server)

	interrupt_channel := make(chan os.Signal, 1)
	signal.Notify(interrupt_channel, os.Interrupt)
	go func() {
		for range interrupt_channel {
			<-server.matchmaker.Stop()

			Info("shutting down game server")
			grpcServer.GracefulStop()
		}
	}()

	Info("starting game server")
	grpcServer.Serve(lis)
}
