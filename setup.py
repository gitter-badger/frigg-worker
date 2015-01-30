# -*- encoding: utf8 -*-
from setuptools import setup, find_packages

setup(
    name='frigg-worker',
    version='0.4.2',
    description='A worker application that listens to the frigg broker '
                'an pick up builds and build them.',
    author='The frigg team',
    author_email='hi@frigg.io',
    license='MIT',
    url='https://github.com/frigg/frigg-worker',
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    install_requires=[
        'frigg-coverage',
        'redis',
        'raven'
    ],
    entry_points={
        'console_scripts': ['frigg-worker = frigg_worker.cli:main']
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
    ]
)
