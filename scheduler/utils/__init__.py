# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from dateutil import parser, tz
from hashlib import sha1
from time import time
import logging
import pytz


logger = logging.getLogger('profiling')


def local_ymd_from_utc_date_string(utc_date_string):
    from_zone = tz.tzutc()
    to_zone = pytz.timezone(getattr(
        settings, 'SCHEDULER_TIMEZONE', "America/Los_Angeles"))
    dt_utc = parser.parse(utc_date_string).replace(tzinfo=from_zone)
    dt_local = dt_utc.astimezone(to_zone)
    return dt_local.strftime('%Y-%m-%d')


def schedule_key(netid, name, external_id, recorder_id, start, end):
    to_sign = '{},{},{},{},{},{},({})'.format(
        netid if netid else '',
        name,
        external_id,
        recorder_id,
        start,
        end,
        getattr(settings, 'PANOPTO_API_TOKEN', ''))

    return sha1(to_sign.encode('utf-8')).hexdigest().upper()


def panopto_app_id():
    return getattr(settings, 'PANOPTO_API_APP_ID', None)


def timer(timed_function):
    def wrapper(*args, **kwargs):
        start_time = time()
        result = timed_function(*args, **kwargs)
        delta_time = time()-start_time
        logger.info(
            "Profile: {} - {}".format(timed_function.__name__, delta_time))
        return result
    return wrapper
