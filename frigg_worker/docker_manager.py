import logging
from docker import Client
from docker.utils import kwargs_from_env
from frigg.helpers import ProcessResult

logger = logging.getLogger(__name__)

class Docker(object):

    def __init__(self):
        self.client = None
        self.container = None

    def set_up_docker(self):
        self.client = Client(**kwargs_from_env())
        self.container = self.client.create_container("ubuntu:latest", command='/bin/sleep 3600')

    def __enter__(self):
        self.set_up_docker()
        self.client.start(self.container.get("Id"))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.stop(self.container.get("Id"))
        self.client.remove_container(self.container.get("Id"))

    def run(self, cmd):

        if not self.container:
            raise AttributeError("Not connected to any docker server")

        result = ProcessResult(command=cmd)
        result.out = self.client.execute(self.container.get("Id"), cmd=cmd)

        result.return_code = 0

        if "docker-exec: failed to exec" in str(result.out):
            result.return_code = 1

        result.succeeded = result.return_code == 0
        logger.debug('Result: {}'.format(result.__dict__))

        return result