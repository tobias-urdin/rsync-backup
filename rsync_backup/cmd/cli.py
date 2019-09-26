# -*- coding: utf-8 -*-

# Copyright (C) 2019 Tobias Urdin
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
import logging
from rsync_backup.config import load_config
from rsync_backup.manager import Manager
from rsync_backup.utils import which
import os
import random
import six
import sys
from timeit import default_timer as timer


LOG = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-c', '--config', type=str, required=True,
                        help='configuration file')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='enable debug output')
    parser.add_argument('-l', '--logfile', type=six.text_type,
                        help='append main run output to a log file')
    parser.add_argument('-n', '--noop', action='store_true',
                        help='only show what would have been done')
    parser.add_argument('-w', '--workers', type=int,
                        help='override amount of workers')
    parser.add_argument('-a', '--allowed-returncodes',
                        type=int, nargs='+', help=('allowed return '
                        'codes, separate by spaces for multiple'))

    args = parser.parse_args()

    if args.debug:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    logfile = None

    if args.logfile is not None:
        logfile = os.path.expanduser(args.logfile)

    start = timer()
    run_id = int(random.getrandbits(32))

    log_format = '%(asctime)s %(levelname)s {} %(message)s'.format(run_id)
    logging.basicConfig(format=log_format, level=loglevel, filename=logfile)

    LOG.info('starting rsync-backup')

    rsync_path = which('rsync')

    if rsync_path is None:
        LOG.error('could not find rsync executable anywhere')
        sys.exit(1)

    LOG.debug('loading configuration file %s' % (args.config))
    config = load_config(args.config)

    workers = config['workers']

    if args.workers is not None:
        LOG.debug('using given workers instead of config')
        workers = args.workers

    LOG.debug('amount of workers is %i' % workers)

    allowed_returncodes = config.get('allowed_returncodes', None)

    if args.allowed_returncodes is not None:
        allowed_returncodes = args.allowed_returncodes
    elif allowed_returncodes is None:
        # default to 0 as allowed return code
        allowed_returncodes = [0]

    LOG.debug('allowed return codes is: %s' % (
              six.text_type(allowed_returncodes)))

    mgr = Manager(rsync_path, workers)
    mgr.queue_jobs(config)

    if args.noop:
        LOG.info('exiting before changes now because of noop arg')
        sys.exit(0)

    for j in mgr.queue:
        j.prepare()

    jobs = mgr.run()

    mgr.wait()

    return_value = 0

    # process time first
    for job_id in jobs:
        job_data = jobs[job_id]
        job_data['end'] = timer()

    success_count = 0
    failed_count = 0

    # now results
    for job_id in jobs:
        job_data = jobs[job_id]

        secs = job_data['end'] - job_data['start']
        mins = secs / 60

        result = job_data['result']

        ready = result.ready()

        if ready is False:
            LOG.error('job %s was never completed due '
                      'to unknown error (%i mins or %i secs)' % (
                      job_id, mins, secs))
            failed_count += 1
            return_value = 1
            continue

        success = result.successful()

        if success:
            job_ret = result.get()

            log_method = LOG.info
            result_str = 'was successful'

            if (allowed_returncodes is not None and
                job_ret not in allowed_returncodes):
                log_method = LOG.error
                result_str = 'failed'
                failed_count += 1
            else:
                success_count += 1

            log_method('job %s %s with return code: %i '
                       '(%i mins or %i secs)' % (
                       job_id, result_str, job_ret, mins, secs))
        else:
            try:
                job_ret = six.text_type(result.get())
            except Exception as exc:
                job_ret = six.text_type(exc)

            LOG.error('job %s was not completed due to '
                      'error: %s (%i mins or %i secs)' % (
                      job_id, job_ret, mins, secs))
            return_value = 1
            failed_count += 1

    total_secs = timer() - start
    total_mins = total_secs / 60

    LOG.info('total job: %i successful: %i failed: %i' % (
             len(jobs), success_count, failed_count))

    LOG.info('run exited with return value: %i (%i mins or %i secs)' % (
             return_value, total_mins, total_secs))

    sys.exit(return_value)
