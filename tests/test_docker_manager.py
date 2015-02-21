from unittest import TestCase
from frigg_worker.docker_manager import Docker
from frigg_worker.jobs import Build

DATA = {
    'id': 2,
    'branch': 'master',
    'sha': 'superbhash',
    'clone_url': 'https://github.com/frigg/test-repo.git',
    'owner': 'frigg',
    'name': 'test-repo',
    }


class DockerManagerTestCase(TestCase):

    def test_context_manager(self):
        build = Build(DATA['id'], DATA)

        with Docker() as docker:
            print(docker.run('apt-get install sfdfsd'))
            print(docker.run('@echo "Everything works"'))
            #print(build.run_tests(docker.run))


build = Build(DATA['id'], DATA)

with Docker() as docker:
    print(docker.run('apt-get install sfdfsd'))
    print(docker.run('@echo "Everything works"'))
    #print(build.run_tests(docker.run))
