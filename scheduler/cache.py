# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from memcached_clients import RestclientPymemcacheClient
import re


ONE_MINUTE = 60
HALF_HOUR = 60 * 30
ONE_HOUR = 60 * 60


class RestClientsCache(RestclientPymemcacheClient):
    def get_cache_expiration_time(self, service, url, status=200):
        if "sws" == service:
            if re.match(r"^/student/v4/term/current", url):
                return ONE_HOUR
            if re.match(r"^/student/v4/term/", url):
                return 10 * ONE_HOUR
            if re.match(r"^/student/v4/course/", url):
                return ONE_HOUR
            if re.match(r"^/student/v4/section", url):
                return ONE_HOUR

        if "pws" == service:
            if re.match(r"^/identity/v1/person/", url):
                return 10 * ONE_HOUR

        if "gws" == service:
            if re.match(r"^/group_sws/v2/group/", url):
                return 2 * ONE_MINUTE

        if "r25" == service:
            if re.match(r"^/r25ws/servlet/wrd/run/event", url):
                return 2 * ONE_MINUTE
            if re.match(r"^/r25ws/servlet/wrd/run/reservation", url):
                return 2 * ONE_MINUTE
            if re.match(r"^/r25ws/servlet/wrd/run/space", url):
                return ONE_HOUR
