# -*- coding: utf8 -*-
import json
import os
import yaml
import logging

from fabric.context_managers import settings, lcd
from frigg import api

from frigg.helpers import local_run, detect_test_runners, cached_property
from .config import config, sentry

logger = logging.getLogger(__name__)


class Result(object):
    log = ''
    return_code = None
    succeeded = None
    task = None

    def __init__(self, task, result=None, error=None):
        self.task = task
        if result:
            self.succeeded = result.succeeded
            self.return_code = result.return_code
            self.log = result
        if error:
            self.log = error

    @classmethod
    def serialize(cls, obj):
        if isinstance(obj, dict):
            return obj
        return obj.__dict__


class Build(object):
    id = ''
    results = []
    cloned = False
    branch = 'master'
    sha = None
    clone_url = None
    name = None
    owner = None
    errored = False

    def __init__(self, id, object):
        self.__dict__.update(object)
        self.id = id
        self.results = []

    @property
    def working_directory(self):
        return os.path.join(config('TMP_DIR'), str(self.id))

    @property
    def succeeded(self):
        if self.errored:
            return False

        for result in self.results:
            if result.succeeded is False:
                return False
        return True

    @cached_property
    def settings(self):
        path = os.path.join(self.working_directory, '.frigg.yml')
        # Default value for project .frigg.yml
        settings = {
            'webhooks': [],
            'comment': False
        }

        try:
            with open(path) as f:
                settings.update(yaml.load(f))
        except IOError:
            settings['tasks'] = detect_test_runners(self)
        return settings

    def run_tests(self):
        self.delete_working_dir()
        if not self.clone_repo():
            return self.error('git clone', 'Access denied')

        try:

            for task in self.settings['tasks']:
                self.run_task(task)
                if self.succeeded is False:
                    # if one task fails, we do not care about the rest
                    break

        except Exception, e:
            self.error('', e)
            sentry.captureException()
        finally:
            self.delete_working_dir()
            self.report_run()
            logger.info("Run of build %s finished." % self.id)

    def clone_repo(self, depth=1):
        local_run("mkdir -p %s" % os.path.dirname(self.working_directory))
        with settings(warn_only=True):
            clone = local_run("git clone --depth=%s --branch=%s %s %s" % (
                depth,
                self.branch,
                self.clone_url,
                self.working_directory
            ))
            if not clone.succeeded:
                message = "Access denied to %s/%s" % (self.owner, self.name)
                logger.error(message)
            return clone.succeeded

    def run_task(self, task_command):
        with settings(warn_only=True):
            with lcd(self.working_directory):
                run_result = local_run(task_command)
                self.results.append(Result(task_command, run_result))

    def delete_working_dir(self):
        if os.path.exists(self.working_directory):
            local_run("rm -rf %s" % self.working_directory)

    def error(self, task, message):
        self.results.append(Result(task, error=message))
        self.errored = True

    def report_run(self):
        api.report_run(json.dumps(self, default=Build.serializer))

    @classmethod
    def serializer(cls, obj):
        out = obj.__dict__
        out['results'] = [Result.serialize(r) for r in obj.results]
        return out
