#!/bin/bash

fig run --rm foreman worker /var/py27/bin/python -m unittest desk.tests.test_worker.WorkerTestCase.test_new_domain
