namespace py ksci.job
namespace go ksci.job

struct LogWrite {
    1: binary job_id
    2: binary log_id
    3: string line
}

struct JobStatusUpdate {
    1: binary job_id
    2: string status
    3: optional string message
}