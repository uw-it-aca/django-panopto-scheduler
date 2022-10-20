# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
from scheduler.utils.loader import load_class_from_module_setting


MEETINGS_MODULE_SETTING = 'MEETING_SCHEDULES_MODULE'


class Meetings(object):
    """Indirection class used to load campus-specific meeting schedule"""
    def __new__(self, courseId):
        return load_class_from_module_setting(
            MEETINGS_MODULE_SETTING, 'Meetings', courseId)


class BaseMeetings(ABC):
    """Base class defines methods necessary for """
    pass
