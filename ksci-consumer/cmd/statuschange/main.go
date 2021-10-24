package main

import (
	"context"
	"log"
	"os"
	"strings"

	"github.com/segmentio/kafka-go"

	"github.com/lbn/ksci/ksci-consumer/data/job"
	"github.com/lbn/ksci/ksci-consumer/service"
)

func readStatusUpdate(data []byte) (statusUpdate *job.JobStatusUpdate, err error) {
	ctx := context.Background()
	statusUpdate = &job.JobStatusUpdate{}
	err = statusUpdate.Read(ctx, service.NewThriftTransport(data))
	return
}

func main() {
	// Cassandra
	session, err := service.NewCassandraSession(strings.Split(os.Getenv("KSCI_CASSANDRA_HOSTS"), " "),
		os.Getenv("KSCI_CASSANDRA_USERNAME"), os.Getenv("KSCI_CASSANDRA_PASSWORD"))
	if err != nil {
		log.Fatal(err)
	}
	defer session.Close()

	r := kafka.NewReader(kafka.ReaderConfig{
		Brokers:   strings.Split(os.Getenv("KSCI_KAFKA_HOSTS"), " "),
		Topic:     "job_status",
		GroupID:   "statusupdate",
		Partition: 0,
		MinBytes:  10e3, // 10KB
		MaxBytes:  10e6, // 10MB
	})
	for {
		m, err := r.ReadMessage(context.Background())
		if err != nil {
			log.Printf("cannot read message: %v", err)
			break
		}
		statusChange, err := readStatusUpdate(m.Value)
		if err != nil {
			log.Printf("err: %v", err)
		}
		jobUUID, err := gocql.UUIDFromBytes(statusChange.JobID)
		if err != nil {
			log.Printf("err: %v", err)
		}
		log.Printf("%s: %s", jobUUID.String(), statusChange.Status)
		err = session.UpdateStatus(statusChange.JobID, statusChange.Status,
			statusChange.Message)
		if err != nil {
			log.Printf("could not update status: %s", err)
		}
	}

	if err := r.Close(); err != nil {
		log.Fatal("failed to close reader:", err)
	}
}
