package service

import (
	"github.com/apache/thrift/lib/go/thrift"
)

func NewThriftTransport(data []byte) *thrift.TBinaryProtocol {
	buffer := thrift.NewTMemoryBuffer()
	buffer.Write(data)
	return thrift.NewTBinaryProtocolConf(buffer, &thrift.TConfiguration{})
}
