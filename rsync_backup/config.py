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
import logging
import six
import sys
import yaml
from voluptuous import Schema, Invalid, Optional


LOG = logging.getLogger(__name__)


def validate_steps(value):
    if not isinstance(value, int):
        raise Invalid('steps must be a integer')

    if value < 0:
        raise Invalid('steps must be zero or above')

    return value


def validate_abs_path(value):
    if not os.path.isdir(value):
        raise Invalid('%s must be a existing directory' % value)

    if not os.path.isabs(value):
        raise Invalid('%s must be a absolute path' % value)

    return value


def validate_exclusions(value):
    if not isinstance(value, list):
        raise Invalid('exclusions must be a list')

    for val in value:
        if not isinstance(val, str):
            raise Invalid('all exclusions must be strings')

    return value


def validate_options(value):
    if not isinstance(value, list):
        raise Invalid('options must be a list')

    for val in value:
        if not isinstance(val, str):
            raise Invalid('all options must be strings')

        if not val.startswith('-'):
            raise Invalid('option %s must start with a dash' % val)

    return value


def validate_allowed_returncodes(value):
    if not isinstance(value, list):
        raise Invalid('allowed_returncodes must be a list')

    for val in value:
        if not isinstance(val, int):
            raise Invalid('all allowed_returncodes must be integers')

    return value


def validate_workers(value):
    if not isinstance(value, int):
        raise Invalid('workers must be a integer')

    if value <= 0:
        raise Invalid('workers must be a positive value '
                      'above zero')

    return value


job_schema = Schema({
    'source': validate_abs_path,
    'destination': validate_abs_path,
    'exclusions': validate_exclusions,
    'options': validate_options,
    'steps': validate_steps,
    Optional('allowed_returncodes'): validate_allowed_returncodes
})

config_schema = Schema({
    'workers': validate_workers,
    'jobs': [job_schema]
})


def load_config(path):
    expanded_path = os.path.expanduser(path)
    if os.path.exists(expanded_path) is False:
        LOG.error('config file %s does not exist' % (
                  expanded_path))
        sys.exit(1)

    try:
        with open(expanded_path) as f:
            data = yaml.safe_load(f)
    except IOError as exc:
        LOG.error('failed to open config file %s: %s' % (
                  expanded_path, six.text_type(exc)))
        sys.exit(1)
    except yaml.YAMLError as exc:
        LOG.error('failed to parse yaml in %s: %s' % (
                  expanded_path, six.text_type(exc)))
        sys.exit(1)
    except Exception as exc:
        LOG.error('failed to load config %s: %s' % (
                  expanded_path, six.text_type(exc)))
        sys.exit(1)

    try:
        config_schema(data)
    except Exception as exc:
        LOG.error('failed to validate config %s: %s' % (
                  expanded_path, six.text_type(exc)))
        sys.exit(1)

    return data
