import typing as tp
import uuid
import enum

import pydantic

from ksci import db


class RunJobStatus(enum.Enum):
    pending = "pending"
    unknown = "unknown"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class RunJob(pydantic.BaseModel):
    id: uuid.UUID
    image: str
    repo: str
    log_id: uuid.UUID
    output_object_id: uuid.UUID
    repo_object_id: uuid.UUID
    steps: tp.List[str]

    class Config:
        orm_mode = True

    @classmethod
    def create(cls, image: str, repo: str, steps: tp.List[str]) -> "RunJob":
        job = cls.from_orm(db.RunJob.create(image=image, repo=repo, steps=steps))
        job.to_status(RunJobStatus.pending)
        return job

    @classmethod
    def load(cls, id: uuid.UUID) -> tp.Optional["RunJob"]:
        runjob = db.RunJob.filter(id=id).first()
        return cls.from_orm(runjob) if runjob else None

    def to_status(self, status: RunJobStatus, message: tp.Optional[str] = None):
        RunJobStatusTransition.update_for_job_id(self.id, status, message)


class RunJobStatusTransition(pydantic.BaseModel):
    job_id: uuid.UUID
    id: uuid.UUID
    status: RunJobStatus
    message: tp.Optional[str]

    class Config:
        orm_mode = True

    @staticmethod
    def update_for_job_id(
        job_id: uuid.UUID, status: RunJobStatus, message: tp.Optional[str] = None
    ):
        db.RunJobStatusTransition.create(
            job_id=job_id, status=status.value, message=message or ""
        )

    @classmethod
    def last_for_job_id(cls, id: uuid.UUID) -> "RunJobStatusTransition":
        return cls.from_orm(
            db.RunJobStatusTransition.filter(job_id=id).limit(1).first()
        )
