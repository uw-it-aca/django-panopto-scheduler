# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
from scheduler.utils.loader import load_class_from_module_setting


COURSES_MODULE_SETTING = 'COURSES_MODULE'


class Course(object):
    """Indirection class used to load campus-specific Course class"""
    def __new__(self, courseId):
        return load_class_from_module_setting(
            COURSES_MODULE_SETTING, 'Course', courseId)


class BaseCourse(ABC):
    """Base class defines methods necessary for pantoto and meetings
       interactions.
    """

    @abstractmethod
    def r25_alien_uid(self):
        """R25 Alien UID unique for each schedulable couse offering"""
        pass

    @abstractmethod
    def canvas_sis_id(self):
        """Canvas SIS_ID assigned to each Canvas course by Student 
        System Provisioning Process"""
        pass

    @abstractmethod
    def panopto_course_external_id(self, start_datetime):
        """Opaque string unique to each course offering."""
        pass

    @abstractmethod
    def panopto_course_folder(self, title):
        """Folder name and folder external_id that must match the values
        set by Panopto Recordings Canvas LTI"""
        pass

    @abstractmethod
    def panopto_course_session(self, start_datetime):
        """Recording session name and external_ id unique to a course
        offering meeting time."""
        pass

    @abstractmethod
    def course_event_title_and_contact(self):
        """Return R25 Aliend ID used for course reference"""
        pass

    def get_crosslisted_course(self):
        return self
