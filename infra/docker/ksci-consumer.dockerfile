FROM golang:1.17-alpine3.14 AS build

WORKDIR /app

COPY go.mod ./
COPY go.sum ./
RUN mkdir /build
RUN go mod download
COPY . ./
RUN go build -o /build/ ./cmd/logwriter
RUN go build -o /build/ ./cmd/statuschange

FROM alpine:3.14
COPY --from=build /build/* /usr/local/bin/