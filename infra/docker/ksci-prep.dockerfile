FROM golang:1.16 AS build-finaliser
WORKDIR /src
COPY ksci-finaliser/ /src/
RUN go build -o /out/ksci-finaliser

FROM alpine:latest
COPY --from=build-finaliser /out/ksci-finaliser /steps-binaries/

