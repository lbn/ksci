package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/apache/thrift/lib/go/thrift"
	"github.com/segmentio/kafka-go"

	"github.com/lbn/ksci/ksci-consumer/data/job"
)

func newTransport(data []byte) *thrift.TBinaryProtocol {
	buffer := thrift.NewTMemoryBuffer()
	buffer.Write(data)
	return thrift.NewTBinaryProtocolConf(buffer, &thrift.TConfiguration{})
}

func readLogWrite(data []byte) (logWrite *job.LogWrite, err error) {
	ctx := context.Background()
	logWrite = &job.LogWrite{}
	err = logWrite.Read(ctx, newTransport(data))
	return
}

func main() {
	// Cassandra
	session, err := newCassandraSession(strings.Split(os.Getenv("KSCI_CASSANDRA_HOSTS"), " "),
		os.Getenv("KSCI_CASSANDRA_USERNAME"), os.Getenv("KSCI_CASSANDRA_PASSWORD"))
	if err != nil {
		log.Fatal(err)
	}
	defer session.Close()

	r := kafka.NewReader(kafka.ReaderConfig{
		Brokers:   strings.Split(os.Getenv("KSCI_KAFKA_HOSTS"), " "),
		Topic:     "logs",
		Partition: 0,
		MinBytes: 10e3, // 10KB
		MaxBytes: 10e6, // 10MB
	})
	for {
		m, err := r.ReadMessage(context.Background())
		if err != nil {
			log.Printf("cannot read message: %v", err)
			break
		}
		logWrite, err := readLogWrite(m.Value)
		if err != nil {
			log.Printf("err: %v", err)
		}
		fmt.Println(logWrite.Line)
		err = session.AppendLog(logWrite.LogID, logWrite.Line)
		if err != nil {
			log.Printf("could not save log to database: %s", err)
		}
	}

	if err := r.Close(); err != nil {
		log.Fatal("failed to close reader:", err)
	}
}
