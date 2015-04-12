# -*- coding: utf-8 -*-
import logging

import requests

logger = logging.getLogger(__name__)


class APIWrapper(object):

    def __init__(self, options):
        self.token = options['hq_token']
        self.url = options['hq_url']

    @property
    def headers(self):
        return {
            'content-type': 'application/json',
            'FRIGG_WORKER_TOKEN': self.token
        }

    def get(self, url):
        return requests.post(url, headers=self.headers)

    def post(self, url, data):
        return requests.post(url, data=data, headers=self.headers)

    def report_run(self, build_id, build):
        response = self.post(self.url, data=build)
        logger.info('Reported build to hq, hq response status-code: %s, data:\n%s' % (
            response.status_code,
            build
        ))
        if response.status_code != 200:
            with open('build-%s-hq-response.html' % build_id, 'w') as f:
                f.write(response.text)
        return response