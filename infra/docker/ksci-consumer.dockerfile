FROM golang:1.17-alpine3.14 AS build

WORKDIR /app

COPY go.mod ./
COPY go.sum ./
RUN go mod download
COPY . ./
RUN go build -o /ksci-consumer

FROM alpine:3.14
COPY --from=build /ksci-consumer /usr/local/bin/ksci-consumer

ENTRYPOINT ["/usr/local/bin/ksci-consumer"]