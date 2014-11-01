import os

from django.conf import settings


class DockerImage(object):
    def __init__(self, client, name):
        self.client = client
        self.name = name

    def get_name(self):
        return self.name+":latest"

    def build(self):
        if not self.exists():
            path = os.path.join(settings.BASE_DIR, "templates")
            return self.client.build(path=path, tag=self.name, stream=False)


    def exists(self):
        for img in self.client.images():
            if self.get_name() in img['RepoTags']:
                return True
        return False

    def remove(self):
        self.client.remove_image(self.get_name())


class DockerContainer(object):
    def __init__(self, client, name):gitggg
        self.client = client
        self.image = DockerImage(client, "frigg_basic")

        self.name = name

        self.id = 2
        self.ssh_port = 15000 + self.id
        self.http_port = 18000 + self.id

        if not self.client.images("frigg_basic"):
            self.image.build()

    def start(self):
        self.client.start(
            self.name,
            port_bindings={80: ("0.0.0.0", self.http_port),
                           22: ("0.0.0.0", self.ssh_port)})

    def stop(self):
        pass

    def create(self):
        self.client.create_container("frigg_basic", name=self.name)

    def exists(self):
        for container in self.client.containers():
            print container
            if container['Id'] == self.id:
                print "id does exist? :O "
                return True

        return False

