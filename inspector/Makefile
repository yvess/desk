build:
	go build -ldflags="-s -w" dinspector.go
	upx -8 dinspector

build_linux:
	docker run --rm -v "$(pwd -P)":/usr/src/inspector -v "$GOPATH":/go -e "GOPATH=/go" -w /usr/src/inspector golang:1.8 go build dinspector.go
	docker run --rm -v "$(pwd -P)":/data lalyos/upx -8 dinspector
