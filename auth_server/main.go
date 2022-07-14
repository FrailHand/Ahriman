package main

import (
	"errors"
	"math/rand"
	"net"
	"strconv"
	"strings"
	"time"
	"crypto/sha512"
	"encoding/base64"

	"gopkg.in/mgo.v2"
	"gopkg.in/mgo.v2/bson"

	"google.golang.org/grpc"

	"golang.org/x/net/context"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/grpclog"

	pb "franmarelli/ahriman/auth_server/server_proto"
	"github.com/robbert229/jwt"
	"google.golang.org/grpc/peer"
	"io/ioutil"
	"os"
	"os/signal"
	"path/filepath"
	"path"
)

const (
	port          = ":51018"
	tokenValidity = 24
	dbHost        = "localhost"
	certPath      = "../certs/server.crt"
	keyPath       = "../certs/server.key"
	secretPath    = "../certs/secret"
)

var (
	basePath   = filepath.Dir(os.Args[0])
	certFile   = path.Join(basePath, certPath)
	keyFile    = path.Join(basePath, keyPath)
	secretFile = path.Join(basePath, secretPath)
)

type AuthServer struct {
	algorithm jwt.Algorithm
	secret    string
	database  *mgo.Session
}

type User struct {
	Pwd      string
	Salt     string
	Remember bool
	Address  string
	Code     string
}

//init the server
func newServer() *AuthServer {
	s := new(AuthServer)
	buff, err := ioutil.ReadFile(secretFile)
	if err != nil {
		Error("could not read the secret file")
		os.Exit(0)
	}
	s.secret = string(buff)
	s.algorithm = jwt.HmacSha512(s.secret)

	s.database, err = mgo.Dial(dbHost)
	if err != nil {
		Error("failed to connect to the database")
		os.Exit(0)
	}
	Info("connected to the auth database")
	return s
}

func (s *AuthServer) Authenticate(user_ID string) (string, error) {
	claims := jwt.NewClaim()
	claims.Set("UserID", user_ID)
	claims.SetTime("exp", time.Now().Add(tokenValidity*time.Hour))

	token, err := s.algorithm.Encode(claims)
	if err != nil {
		Error("failed to encode token with HMAC-SHA 512")
		return "", err
	}

	Info("player connected - %v", user_ID)
	return token, nil
}

func GetIP(ctx context.Context) (string, error) {
	client, ok := peer.FromContext(ctx)
	if !ok {
		Error("failed to read peer from context")
		return "", errors.New("context error: could not read peer")
	}
	string_addr := client.Addr.String()
	return strings.Split(string_addr, ":")[0], nil
}

func CheckHash(password string, salt string) string {
	payload := append([]byte(password), []byte(salt)...)
	hash := sha512.Sum512(payload)
	hash_string := base64.StdEncoding.EncodeToString(hash[:])
	return hash_string
}

func (s *AuthServer) Authentication(
	ctx context.Context, request *pb.AuthRequest) (
	*pb.AuthResponse, error) {

	collec := s.database.DB("ahriman").C("credentials")

	var result []User
	err := collec.FindId(request.UserId).All(&result)

	if err != nil {
		Error("query error : %v", err)
		return nil, err
	}
	if len(result) == 0 {
		Warning("invalid user tried to connect - %v", request.UserId)
		return &pb.AuthResponse{Response: &pb.AuthResponse_Available{Available: false}}, nil
	}

	if result[0].Remember {
		ip_addr, err := GetIP(ctx)
		if err != nil {
			return nil, err
		}

		if ip_addr == result[0].Address && request.Password == result[0].Code {
			token, err := s.Authenticate(request.UserId)
			if err != nil {
				return nil, err
			}
			return &pb.AuthResponse{Response: &pb.AuthResponse_Payload{&pb.AuthCredentials{Token: token, Code: ""}}}, nil
		}
	}

	hash := CheckHash(request.Password, result[0].Salt)
	if hash == result[0].Pwd {
		token, err := s.Authenticate(request.UserId)
		if err != nil {
			return nil, err
		}
		code := ""

		if request.Remember {
			ip_addr, err := GetIP(ctx)
			if err != nil {
				return nil, err
			}

			code = strconv.Itoa(int(rand.Int31()))
			_, err = collec.UpsertId(request.UserId, bson.M{
				"$set": bson.M{"address": ip_addr, "code": code, "remember": true}})
			if err != nil {
				Error("could not update IP in database - %v", err)
				return nil, err
			}
		} else if result[0].Remember {
			_, err = collec.UpsertId(request.UserId, bson.M{
				"$set": bson.M{"remember": false}})
			if err != nil {
				Error("could not update remember in database - %v", err)
				return nil, err
			}
		}

		return &pb.AuthResponse{Response: &pb.AuthResponse_Payload{&pb.AuthCredentials{Token: token, Code: code}}}, nil
	}

	return &pb.AuthResponse{Response: &pb.AuthResponse_Available{Available: false}}, nil
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
	pb.RegisterAuthServer(grpcServer, server)

	interrupt_channel := make(chan os.Signal, 1)
	signal.Notify(interrupt_channel, os.Interrupt)
	go func() {
		for range interrupt_channel {
			Info("shutting down authentication server")
			grpcServer.GracefulStop()
		}
	}()

	Info("starting authentication server")
	grpcServer.Serve(lis)
}
