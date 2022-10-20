# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import ugettext as _

"""
Custom exceptions used by Scheduler.
"""


class InvalidUser(Exception):
    pass


class StudentWebServiceUnavailable(Exception):
    def __str__(self):
        return _("sws_not_available")


class CourseEventException(Exception):
    pass


class RecorderException(Exception):
    pass


class MissingParamException(Exception):
    pass


class InvalidParamException(Exception):
    pass


class ValidationException(Exception):
    pass


class PanoptoUserException(Exception):
    pass
