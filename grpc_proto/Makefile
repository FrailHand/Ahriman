all:
	make game_server
	make auth_server
	make client

game_server:
	protoc -I . ./server_proto.proto --go_out=plugins=grpc:${GOPATH}/src/franmarelli/ahriman/game_server/server_proto

auth_server:
	protoc -I . ./server_proto.proto --go_out=plugins=grpc:${GOPATH}/src/franmarelli/ahriman/auth_server/server_proto

client:
	python -m grpc_tools.protoc -I./ --python_out=../client/ahriman/communication/grpc_proto/ --grpc_python_out=../client/ahriman/communication/grpc_proto/ ./server_proto.proto
	sed -i 's/import.*as/from . &/' ../client/ahriman/communication/grpc_proto/*_pb2_grpc.py

install:
	go get -u google.golang.org/grpc
	go get -u github.com/golang/protobuf/protoc-gen-go
