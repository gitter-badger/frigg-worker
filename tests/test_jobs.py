# -*- coding: utf8 -*-
import unittest

import mock
from docker.helpers import ProcessResult
from docker.manager import Docker
from raven import Client

from frigg_worker.jobs import Build, Result

DATA = {
    'id': 1,
    'branch': 'master',
    'sha': 'superbhash',
    'clone_url': 'https://github.com/frigg/test-repo.git',
    'owner': 'frigg',
    'name': 'test-repo',
}

BUILD_SETTINGS_WITH_NO_SERVICES = {
    'setup_tasks': [],
    'tasks': ['tox'],
    'services': [],
    'coverage': {'path': 'coverage.xml', 'parser': 'python'}
}

BUILD_SETTINGS_ONE_SERVICE = {
    'setup_tasks': [],
    'tasks': ['tox'],
    'services': ['redis-server'],
    'coverage': None,
}

BUILD_SETTINGS_FOUR_SERVICES = {
    'setup_tasks': [],
    'tasks': ['tox'],
    'services': ['redis-server', 'postgresql', 'nginx', 'mongodb'],
    'coverage': None,
}

BUILD_SETTINGS_SERVICES_AND_SETUP = {
    'setup_tasks': ['apt-get install nginx'],
    'tasks': ['tox'],
    'services': ['redis-server', 'postgresql', 'nginx', 'mongodb'],
    'coverage': None,
}

WORKER_OPTIONS = {
    'dispatcher_url': 'http://example.com/dispatch',
    'dispatcher_token': 'tokened',
    'hq_url': 'http://example.com/hq',
    'hq_token': 'tokened',
}


class BuildTestCase(unittest.TestCase):
    def setUp(self):
        self.docker = Docker()
        self.build = Build(1, DATA, self.docker, WORKER_OPTIONS)

    def test_init(self):
        self.assertEquals(self.build.id, 1)
        self.assertEquals(len(self.build.results), 0)
        self.assertEquals(self.build.branch, DATA['branch'])
        self.assertEquals(self.build.sha, DATA['sha'])
        self.assertEquals(self.build.sha, DATA['sha'])
        self.assertEquals(self.build.clone_url, DATA['clone_url'])
        self.assertEquals(self.build.owner, DATA['owner'])
        self.assertEquals(self.build.name, DATA['name'])

    def test_error(self):
        self.build.error('tox', 'Command not found')
        self.assertEquals(len(self.build.results), 1)
        self.assertTrue(self.build.errored)
        self.assertFalse(self.build.results['tox'].succeeded)
        self.assertEquals(self.build.results['tox'].log, 'Command not found')
        self.assertEquals(self.build.results['tox'].task, 'tox')

    @mock.patch('docker.manager.Docker.start')
    @mock.patch('docker.manager.Docker.stop')
    @mock.patch('docker.manager.Docker.run')
    def test_succeeded(self, mock_docker_run, mock_docker_stop, mock_docker_start):
        success = Result('tox')
        success.succeeded = True
        failure = Result('flake8')
        failure.succeeded = False
        self.build.results['tox'] = success
        self.assertTrue(self.build.succeeded)
        self.build.results['flake8'] = failure
        self.assertFalse(self.build.succeeded)

    @mock.patch('docker.manager.Docker.start')
    @mock.patch('docker.manager.Docker.stop')
    @mock.patch('frigg_worker.jobs.parse_coverage')
    @mock.patch('frigg_worker.jobs.Build.clone_repo')
    @mock.patch('frigg_worker.jobs.Build.run_task')
    @mock.patch('docker.manager.Docker.read_file')
    @mock.patch('frigg_worker.jobs.Build.report_run', lambda *x: None)
    @mock.patch('frigg_worker.jobs.build_settings', lambda *x: BUILD_SETTINGS_WITH_NO_SERVICES)
    def test_run_tests(self, mock_read_file, mock_run_task, mock_clone_repo,
                       mock_parse_coverage, mock_docker_stop, mock_docker_start):
        self.build.run_tests()
        mock_run_task.assert_called_once_with('tox')
        mock_clone_repo.assert_called_once()
        mock_read_file.assert_called_once_with('builds/1/coverage.xml')
        mock_parse_coverage.assert_called_once()
        self.assertTrue(self.build.succeeded)
        self.assertTrue(self.build.finished)

    @mock.patch('frigg_worker.jobs.Build.clone_repo')
    @mock.patch('frigg_worker.jobs.Build.run_task', side_effect=OSError())
    @mock.patch('frigg_worker.jobs.Build.report_run', lambda *x: None)
    @mock.patch('frigg_worker.jobs.build_settings', lambda *x: BUILD_SETTINGS_WITH_NO_SERVICES)
    def test_run_tests_fail_task(self, mock_run_task, mock_clone_repo):
        self.build.run_tests()
        mock_clone_repo.assert_called_once()
        mock_run_task.assert_called_once_with('tox')
        self.assertFalse(self.build.succeeded)
        self.assertTrue(self.build.finished)

    @mock.patch('frigg_worker.jobs.Build.run_task')
    @mock.patch('frigg_worker.jobs.Build.clone_repo', lambda x: False)
    def test_run_tests_fail_clone(self, mock_run_task):
        self.build.run_tests()
        self.assertFalse(mock_run_task.called)
        self.assertFalse(self.build.succeeded)

    @mock.patch('frigg_worker.api.APIWrapper.report_run')
    @mock.patch('frigg_worker.jobs.Build.serializer', lambda *x: {})
    @mock.patch('frigg_worker.jobs.build_settings', lambda *x: {})
    def test_report_run(self, mock_report_run):
        self.build.report_run()
        mock_report_run.assert_called_once_with(1, '{}')

    @mock.patch('docker.manager.Docker.directory_exist')
    @mock.patch('docker.manager.Docker.run')
    def test_delete_working_dir(self, mock_local_run, mock_directory_exist):
        self.build.delete_working_dir()
        mock_directory_exist.assert_called_once()
        mock_local_run.assert_called_once_with('rm -rf builds/1')

    @mock.patch('docker.manager.Docker.run')
    def test_run_task(self, mock_local_run):
        self.build.results['tox'] = Result('tox')
        self.build.run_task('tox')
        mock_local_run.assert_called_once_with('tox', 'builds/1')
        self.assertEqual(len(self.build.results), 1)
        self.assertEqual(self.build.results['tox'].task, 'tox')
        self.assertEqual(self.build.results['tox'].pending, False)

    @mock.patch('docker.manager.Docker.run')
    def test_clone_repo_regular(self, mock_local_run):
        self.build.clone_repo(1)
        mock_local_run.assert_called_once_with(
            'git clone --depth=1 --branch=master https://github.com/frigg/test-repo.git builds/1'
        )

    @mock.patch('docker.manager.Docker.start')
    @mock.patch('docker.manager.Docker.stop')
    @mock.patch('docker.manager.Docker.run')
    def test_clone_repo_pull_request(self, mock_local_run, mock_docker_stop, mock_docker_start):
        self.build.pull_request_id = 2
        self.build.clone_repo(1)
        mock_local_run.assert_called_once_with(
            'git clone --depth=1 https://github.com/frigg/test-repo.git builds/1 && cd builds/1 && '
            'git fetch origin pull/2/head:pull-2 && git checkout pull-2'
        )

    @mock.patch('frigg_worker.jobs.build_settings', lambda *x: BUILD_SETTINGS_WITH_NO_SERVICES)
    def test_serializer(self):
        self.build.worker_options['sentry'] = Client()
        serialized = Build.serializer(self.build)
        self.assertEqual(serialized['id'], self.build.id)
        self.assertEqual(serialized['finished'], self.build.finished)
        self.assertEqual(serialized['owner'], self.build.owner)
        self.assertEqual(serialized['name'], self.build.name)
        self.assertEqual(serialized['results'], [])
        self.assertNotIn('worker_options', serialized)
        self.assertNotIn('docker', serialized)
        self.assertNotIn('api', serialized)

        self.build.tasks.append('tox')
        self.build.results['tox'] = Result('tox')
        serialized = Build.serializer(self.build)
        self.assertEqual(serialized['setup_results'], [])
        self.assertEqual(serialized['results'], [{'task': 'tox', 'pending': True}])

        result = ProcessResult('tox')
        result.out = 'Success'
        result.return_code = 0
        self.build.results['tox'].update_result(result)
        self.assertEqual(serialized['results'], [{'task': 'tox', 'pending': False, 'log': 'Success',
                                                  'return_code': 0, 'succeeded': True}])

        self.assertEqual(serialized['setup_results'], [])

    @mock.patch('frigg_worker.jobs.build_settings', lambda *x: BUILD_SETTINGS_SERVICES_AND_SETUP)
    def test_serializer_with_setup_and_tasks(self):
        self.build.worker_options['sentry'] = Client()

        self.build.tasks.append('tox')
        self.build.setup_tasks.append('apt-get install nginx')
        self.build.results['tox'] = Result('tox')
        self.build.setup_results['apt-get install nginx'] = Result('apt-get install nginx')
        serialized = Build.serializer(self.build)
        self.assertEqual(serialized['setup_results'], [{'task': 'apt-get install nginx',
                                                        'pending': True}])
        self.assertEqual(serialized['results'], [{'task': 'tox', 'pending': True}])

        result = ProcessResult('tox')
        result.out = 'Success'
        result.return_code = 0
        self.build.results['tox'].update_result(result)

        setup_result = ProcessResult('apt-get install nginx')
        setup_result.out = 'Success'
        setup_result.return_code = 0
        self.build.setup_results['apt-get install nginx'].update_result(setup_result)

        self.assertEqual(serialized['results'], [{'task': 'tox', 'pending': False, 'log': 'Success',
                                                  'return_code': 0, 'succeeded': True}])

        self.assertEqual(serialized['setup_results'], [{'task': 'apt-get install nginx',
                                                        'pending': False, 'log': 'Success',
                                                        'return_code': 0, 'succeeded': True}])

    @mock.patch('docker.manager.Docker.start')
    @mock.patch('docker.manager.Docker.stop')
    @mock.patch('docker.manager.Docker.run')
    @mock.patch('frigg_worker.jobs.build_settings', lambda *x: BUILD_SETTINGS_WITH_NO_SERVICES)
    def test_start_no_services(self, mock_docker_run, mock_docker_stop, mock_docker_start):
        self.build.start_services()
        self.assertFalse(mock_docker_run.called)

    @mock.patch('docker.manager.Docker.run')
    @mock.patch('frigg_worker.jobs.build_settings', lambda *x: BUILD_SETTINGS_ONE_SERVICE)
    def test_start_one_service(self, mock_docker_run):
        self.build.start_services()
        mock_docker_run.assert_called_once_with('sudo service redis-server start')

    @mock.patch('frigg_worker.jobs.logger.warning')
    @mock.patch('frigg_worker.jobs.build_settings', lambda *x: BUILD_SETTINGS_ONE_SERVICE)
    def test_start_unknown_service(self, mock_logger_warning):
        failed_result = ProcessResult('tox')
        failed_result.return_code = 1
        with mock.patch('docker.manager.Docker.run', lambda *x: failed_result):
            self.build.start_services()
            mock_logger_warning.assert_called_with('Service "redis-server" did not start.')

    @mock.patch('docker.manager.Docker.run')
    @mock.patch('frigg_worker.jobs.build_settings', lambda *x: BUILD_SETTINGS_FOUR_SERVICES)
    def test_start_four_services_in_order(self, mock_docker_run):
        self.build.start_services()

        mock_docker_run.assert_has_calls([
            mock.call('sudo service redis-server start'),
            mock.call().succeeded.__bool__(),
            mock.call('sudo service postgresql start'),
            mock.call().succeeded.__bool__(),
            mock.call('sudo service nginx start'),
            mock.call().succeeded.__bool__(),
            mock.call('sudo service mongodb start'),
            mock.call().succeeded.__bool__(),
        ])

    @mock.patch('frigg_worker.jobs.build_settings', lambda *x: BUILD_SETTINGS_SERVICES_AND_SETUP)
    def test_create_pending_tasks_splitted_into_setup_tasks_and_tasks(self):
        self.assertEqual([], self.build.tasks)
        self.assertEqual([], self.build.setup_tasks)
        self.build.create_pending_tasks()
        self.assertEqual(["apt-get install nginx"], self.build.setup_tasks)
        self.assertEqual(["tox"], self.build.tasks)

    @mock.patch('docker.manager.Docker.run')
    @mock.patch('frigg_worker.jobs.Build.delete_working_dir', lambda x: True)
    @mock.patch('frigg_worker.jobs.Build.clone_repo', lambda x: True)
    @mock.patch('frigg_worker.jobs.Build.parse_coverage', lambda x: True)
    @mock.patch('frigg_worker.jobs.Build.report_run', lambda x: None)
    @mock.patch('frigg_worker.jobs.build_settings', lambda *x: BUILD_SETTINGS_SERVICES_AND_SETUP)
    def test_build_setup_steps(self, mock_docker_run):
        self.build.run_tests()

        mock_docker_run.assert_has_calls([
            mock.call('sudo service redis-server start'),
            mock.call().succeeded.__bool__(),
            mock.call('sudo service postgresql start'),
            mock.call().succeeded.__bool__(),
            mock.call('sudo service nginx start'),
            mock.call().succeeded.__bool__(),
            mock.call('sudo service mongodb start'),
            mock.call().succeeded.__bool__(),
            mock.call('apt-get install nginx', self.build.working_directory),
            mock.call('tox', self.build.working_directory),
        ])


class ResultTestCase(unittest.TestCase):
    def test_update_result_success(self):
        result = ProcessResult('tox')
        result.out = 'Success'
        result.return_code = 0
        success = Result('tox')
        success.update_result(result)
        self.assertTrue(success.succeeded)
        self.assertEquals(success.log, 'Success')
        self.assertEquals(success.task, 'tox')

    def test_update_result_failure(self):
        result = ProcessResult('tox')
        result.out = 'Oh snap'
        result.return_code = 1
        failure = Result('tox')
        failure.update_result(result)
        self.assertFalse(failure.succeeded)
        self.assertEquals(failure.log, 'Oh snap')
        self.assertEquals(failure.task, 'tox')

    def test_update_error(self):
        error = Result('tox')
        error.update_error('Command not found')
        self.assertFalse(error.succeeded)
        self.assertEquals(error.log, 'Command not found')
        self.assertEquals(error.task, 'tox')

    def test_serialize(self):
        error = Result('tox')
        error.update_error('Command not found')
        self.assertEqual(Result.serialize(error), error.__dict__)
        self.assertEqual(Result.serialize(Result.serialize(error)), error.__dict__)
