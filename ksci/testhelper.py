import os


def configure():
    os.environ["KSCI_RABBITMQ_HOST"] = ""
    os.environ["KSCI_RABBITMQ_PASSWORD"] = ""
    os.environ["KSCI_RABBITMQ_USERNAME"] = ""
    os.environ["KSCI_CASSANDRA_HOSTS"] = "localhost"
    os.environ["KSCI_REDIS_HOST"] = ""
    os.environ["KSCI_URL"] = "localhost"
