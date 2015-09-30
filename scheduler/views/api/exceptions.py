from django.utils.translation import ugettext as _

"""
Custom exceptions used by Panopto Scheduler.
"""


class MissingParamException(Exception):
    pass


class InvalidParamException(Exception):
    pass
