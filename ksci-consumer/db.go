package main

import (
	"github.com/gocql/gocql"
)

type cassandra struct {
	session *gocql.Session
}

func newCassandraSession(hosts []string, username, password string) (*cassandra, error) {
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
