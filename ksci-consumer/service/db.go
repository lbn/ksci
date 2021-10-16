package service

import (
	"github.com/gocql/gocql"
)

type cassandra struct {
	session *gocql.Session
}

func NewCassandraSession(hosts []string, username, password string) (*cassandra, error) {
	cluster := gocql.NewCluster(hosts...)
	cluster.Keyspace = "ksci"
	cluster.Authenticator = gocql.PasswordAuthenticator{
		Username: username,
		Password: password,
	}
	session, err := cluster.CreateSession()
	if err != nil {
		return nil, err
	}
	return &cassandra{session: session}, nil
}

func (cass *cassandra) Close() {
	cass.session.Close()
}

func (cass *cassandra) AppendLog(logID []byte, line string) error {
	logUUID, err := gocql.UUIDFromBytes(logID)
	if err != nil {
		return err
	}
	return cass.session.Query(`INSERT INTO logs (id, time, log) VALUES (?, ?, ?)`, logUUID,
		gocql.TimeUUID(), line).Exec()
}

func (cass *cassandra) UpdateStatus(jobID []byte, status string, message *string) error {
	jobUUID, err := gocql.UUIDFromBytes(jobID)
	if err != nil {
		return err
	}
	statusMessage := ""
	if message != nil {
		statusMessage = *message
	}
	return cass.session.Query(`INSERT INTO run_job_status_transition (job_id, id, status, message) VALUES (?, ?, ?, ?)`,
		jobUUID, gocql.TimeUUID(), status, statusMessage).Exec()
}
