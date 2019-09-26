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

import copy
import logging
import multiprocessing
from rsync_backup.job import Job, backup_job
from rsync_backup.rsync import get_rsync_command
import os
from timeit import default_timer as timer
import uuid


LOG = logging.getLogger(__name__)


class Manager(object):
    def __init__(self, rsync_path, workers=1):
        self.rsync_path = rsync_path
        self.pool = multiprocessing.Pool(processes=workers)
        self.queue = []

    def _process_steps(self, job):
        src = job.get('source')
        dst = job.get('destination')

        steps = job.get('steps')

        last_dirs = [src]
        new_sources = []

        while (steps > 0):
            new_dirs = []

            for dir in last_dirs:
                objs = os.listdir(dir)

                for obj in objs:
                    obj_path = os.path.join(dir, obj)

                    if not os.path.isdir(obj_path):
                        continue

                    new_dirs.append(obj_path)

            steps -= 1

            if steps == 0:
                new_sources = new_dirs
            else:
                last_dirs = new_dirs

        new_jobs = []

        for new_src in new_sources:
            src_path_diff = os.path.relpath(new_src, src)
            new_dst = os.path.join(dst, src_path_diff)

            new_job = copy.deepcopy(job)
            new_job['source'] = new_src
            new_job['destination'] = new_dst
            new_job['parent_source'] = src
            new_job['parent_destination'] = dst
            new_job['exploded'] = True

            new_jobs.append(new_job)

        return new_jobs

    def _explode_jobs(self, jobs):
        exploded_jobs = []

        for j in jobs:
            steps = j.get('steps')

            if steps > 0:
                exploded_jobs += self._process_steps(j)
            else:
                j['exploded'] = False
                exploded_jobs.append(j)

        return exploded_jobs

    def queue_jobs(self, config):
        jobs = config['jobs']

        exploded_jobs = self._explode_jobs(jobs)

        for j in exploded_jobs:
            job = Job(j)

            LOG.info('adding job %s %s -> %s to queue' % (
                     job.id, job.source, job.destination))

            rsync_command = get_rsync_command(self.rsync_path,
                job.source, job.destination, job.exclusions,
                options=job.options)
            LOG.debug('job %s rsync command: %s' % (
                      job.id, ' '.join(rsync_command)))

            self.queue.append(job)

    def run(self):
        results = {}

        for job in self.queue:
            args = (self.rsync_path, job.source, job.destination,
                    job.exclusions, job.options)
            res = self.pool.apply_async(backup_job, args=args)
            job_data = {
                'start': timer(),
                'result': res
            }
            results[job.id] = job_data

        self.pool.close()
        return results

    def wait(self):
        LOG.info('main process is now waiting for jobs to complete...')
        self.pool.join()
