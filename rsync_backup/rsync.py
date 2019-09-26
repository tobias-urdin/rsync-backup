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

import os
import six
import subprocess


def strip_trailing_slash(directory):
    return (directory[:-1]
            if directory.endswith('/')
            else directory)


def add_trailing_slash(directory):
    return (directory
            if directory.endswith('/')
            else '{}/'.format(directory))


def sanitize_trailing_slash(source_dir, target_dir, sync_sourcedir_contents):
    target_dir = strip_trailing_slash(target_dir)

    if sync_sourcedir_contents:
        source_dir = add_trailing_slash(source_dir)
    else:
        source_dir = strip_trailing_slash(source_dir)

    return [source_dir, target_dir]


def get_exclusions(exclusions=[]):
    result = []

    for exclude in exclusions:
        exclude_contains = (exclude.startswith('--exclude') or # noqa
                            exclude.startswith('--exclude=')) # noqa
        if exclude_contains:
            result.append(exclude)
        else:
            excl = '--exclude={}'.format(exclude)
            result.append(excl)

    return result


def get_rsync_command(rsync_path, source, destination, exclusions=[],
                      sync_source_contents=True, options=[]):
    if os.path.isfile(source):
        sync_source_contents = False

    dirs = sanitize_trailing_slash(source, destination,
                                   sync_source_contents)

    exclusions = get_exclusions(exclusions)

    rsync_command = [rsync_path]
    return (rsync_command + options + exclusions + dirs)


def run_rsync(rsync_path, source, destination, exclusions=[],
              sync_source_contents=True, options=[]):
    rsync_command = get_rsync_command(
        rsync_path, source, destination, exclusions,
        sync_source_contents, options)

    ret_code = 0

    if six.PY2:
        ret_code = subprocess.call(rsync_command, stdout=subprocess.PIPE)
    else:
        process = subprocess.run(rsync_command, stdout=subprocess.PIPE)
        ret_code = process.returncode

    return ret_code
