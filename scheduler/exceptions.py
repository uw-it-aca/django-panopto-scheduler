# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext as _

"""
Custom exceptions used by Scheduler.
"""


class InvalidUser(Exception):
    pass


class StudentWebServiceUnavailable(Exception):
    def __str__(self):
        return _("sws_not_available")
