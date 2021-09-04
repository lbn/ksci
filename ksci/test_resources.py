from ksci import testhelper

testhelper.configure()

from ksci.resources import *


class TestRunJob:
    def test_basic(self):
        job = RunJob.create(
            "golang:latest",
            "https://github.com/my/repo",
            ["echo hello 1", "echo hello 2",],
        )
        assert (
            RunJobStatusTransition.last_for_job_id(job.id).status
            == RunJobStatus.pending
        )
        assert RunJob.load(job.id) == job
        job.to_status(RunJobStatus("running"))
        assert (
            RunJobStatusTransition.last_for_job_id(job.id).status
            == RunJobStatus.running
        )
