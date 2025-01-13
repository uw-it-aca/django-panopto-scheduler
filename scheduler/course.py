# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

#
# Course reflects the attributes necessary to correlate a
# specific course offering's meeting schedule with
# Panopto recording sessions, the facilities scheduling system,
# and Canvas LMS.
#

from abc import ABC, abstractmethod
from scheduler.utils.loader import load_class_from_module_setting


COURSES_MODULE_SETTING = 'COURSES_MODULE'


class Course(object):
    """Indirection class used to load campus-specific Course class"""
    def __new__(self, courseId):
        return load_class_from_module_setting(
            COURSES_MODULE_SETTING, 'Course', courseId)


class BaseCourse(ABC):
    """Base class definining methods necessary to associate a course
    offering with the course meeting location and panopto folder and
    scheduled recording sessions
    """

    @abstractmethod
    def reservation_uid(self):
        """ID used to reference the course offering in the reservation
        system. For R25 this is would be the Alien UID unique for
        the couse offering.
        """
        pass

    @abstractmethod
    def panopto_course_external_id(self, start_datetime):
        """Opaque string unique to each course offering."""
        pass

    @abstractmethod
    def panopto_course_folder(self, title):
        """Folder name and folder external_id that must match the values
        set by Panopto's Recordings LTI
        """
        pass

    @abstractmethod
    def panopto_course_session(self, start_datetime):
        """Recording session name and external_id unique to a course
        offering meeting time.
        """
        pass

    @abstractmethod
    def get_crosslisted_course(self):
        """If the Course is crosslisted (joined), return the Course
        class corresponding to the course crosslisted are linked into
        """
        return self
