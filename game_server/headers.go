package main

import (
	"google.golang.org/grpc/metadata"
	"errors"
	"context"
	"github.com/robbert229/jwt"
	"io/ioutil"
	"os"
)

type JWT_arbiter struct {
	algorithm jwt.Algorithm
}

func NewArbiter() *JWT_arbiter {
	s := new(JWT_arbiter)
	buff, err := ioutil.ReadFile(secretFile)
	if err != nil {
		Error("could not read the secret file")
		os.Exit(0)
	}
	secret := string(buff)
	s.algorithm = jwt.HmacSha512(secret)
	return s
}

func (s *JWT_arbiter) ValidateToken(token string) (string, error) {
	if err := s.algorithm.Validate(token); err != nil {
		Warning(token)
		Warning("invalid token received - %v", err)
		return "", err
	}

	loadedClaims, err := s.algorithm.Decode(token)
	if err != nil {
		Error("could not decode token - %v", err)
		return "", err
	}

	userID_buf, err := loadedClaims.Get("UserID")
	if err != nil {
		Error("invalid token field: UserID - %v", err)
		return "", err
	}

	userID, ok := userID_buf.(string)
	if !ok {
		Error("userID is not a string")
		return "", err
	}

	return userID, nil
}

//read the metadata and authenticate the player
func (s *JWT_arbiter) Authenticate(context context.Context) (metadata.MD, string, error) {
	headers, ok := metadata.FromIncomingContext(context)
	if !ok {
		Error("could not fetch metadata for authentication")
		return nil, "", errors.New("Metadata fetch error")
	}

	token, ok := headers["token"]
	if !ok || len(token) != 1 {
		Warning("invalid metadata from GameStream : token field")
		return nil, "", errors.New("Invalid metadata : token field")
	}

	userID, err := s.ValidateToken(token[0])
	if err != nil {
		return nil, "", err
	}

	return headers, userID, nil
}

//read a field in the header
func ReadHeader(headers metadata.MD, field string) (string, error) {
	meta, ok := headers[field]
	if !ok || len(meta) != 1 {
		Warning(
			"invalid metadata : %v field",
			field)
		return "", errors.New("Invalid metadata")
	}
	return meta[0], nil
}
