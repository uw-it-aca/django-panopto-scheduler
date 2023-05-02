# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from dateutil import parser, tz
from hashlib import sha1
import pytz


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
