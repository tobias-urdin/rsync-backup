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

import logging
from rsync_backup.rsync import run_rsync
import os
import uuid
import sys
import six
from timeit import default_timer as timer


LOG = logging.getLogger(__name__)


class DestinationPath(object):
    def __init__(self, path, uid, gid, mode):
        self.path = path
        self.uid = uid
        self.gid = gid
        self.mode = mode

    def create(self):
        if not os.path.isdir(self.path):
            os.mkdir(self.path)
            os.chown(self.path, self.uid, self.gid)
            os.chmod(self.path, self.mode)


class Job(object):
    def __init__(self, data):
        self.id = six.text_type(uuid.uuid4())
        self.source = data.get('source')
        self.destination = data.get('destination')
        self.exclusions = data.get('exclusions')
        self.options = data.get('options')
        self.exploded = data.get('exploded', False)
        self.parent_source = data.get('parent_source', None)
        self.parent_destination = data.get('parent_destination', None)

        self.destination_paths = []

        self._process_destination()

    def _process_destination(self):
        # If it was not exploded we dont need to fix anything on
        # the destination.
        if self.exploded is False:
            return

        parent_dst_diff = os.path.relpath(self.destination,
                                          self.parent_destination)
        normalized_dst_diff = os.path.normpath(parent_dst_diff)

        all_parts = normalized_dst_diff.split(os.sep)

        previous_dest = self.parent_destination
        previous_src = self.parent_source

        for part in all_parts:
            part_path = os.path.join(previous_dest, part)

            if not os.path.isdir(part_path):
                source_part = os.path.join(previous_src, part)
                LOG.debug('source_part is %s' % source_part)

                if not os.path.isdir(source_part):
                    LOG.error('cannot create destination %s because '
                              'source %s does not exist' %
                              (part_path, source_part))
                    sys.exit(1)

                source_part_stat = os.stat(source_part)

                LOG.info('this run will create destination dir: {} '
                         'with owner {} group: {} and '
                         'mode: {:o}'.format(
                             part_path, source_part_stat.st_uid,
                             source_part_stat.st_gid,
                             source_part_stat.st_mode))

                new_dest_path = DestinationPath(part_path,
                                                source_part_stat.st_uid,
                                                source_part_stat.st_gid,
                                                source_part_stat.st_mode)

                LOG.debug('adding destination path %s (uid: %i gid: %i '
                          ' mode: %i) for creation' %
                          (part_path, source_part_stat.st_uid,
                           source_part_stat.st_gid,
                           source_part_stat.st_mode))

                previous_src = os.path.join(previous_src, part)
                self.destination_paths.append(new_dest_path)

            previous_dest = part_path

    def prepare(self):
        if len(self.destination_paths) <= 0:
            return

        for dest_path in self.destination_paths:
            try:
                dest_path.create()
            except Exception as exc:
                LOG.error('failed to prepare destination path %s: %s' % (
                          dest_path.path, six.text_type(exc)))
                sys.exit(1)


def backup_job(rsync_path, source, dest, exclusions, options):
    start = timer()
    result = run_rsync(rsync_path, source, dest, exclusions,
                       options=options)
    end = timer()
    return result, (end - start)
