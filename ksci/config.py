import environ


@environ.config(prefix="KSCI")
class AppConfig:
    url = environ.var()

    @environ.config
    class Redis:
        host = environ.var()
        port = environ.var(default=6379)

        @property
        def url(self):
            return f"redis://{self.host}:{self.port}/0"

    @environ.config
    class RabbitMQ:
        host = environ.var()
        username = environ.var()
        password = environ.var()
        port = environ.var(default=5672)

        @property
        def url(self):
            return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}//"

    rabbitmq: RabbitMQ = environ.group(RabbitMQ)
    redis: Redis = environ.group(Redis)


import os

print(os.environ)
config: AppConfig = AppConfig.from_environ()
