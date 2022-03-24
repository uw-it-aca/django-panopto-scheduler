# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from scheduler.views.api.exceptions import MissingParamException
from scheduler.views.api.exceptions import InvalidParamException
from scheduler.models import Course
from uw_sws.models import Term
import re


class ValidationException(Exception):
    pass


class Validation(object):
    """  Validates Panopto Id format and various course parameters
    """

    def course_id(self, course_id):
        if not course_id:
            raise MissingParamException('missing course id')
        course_parts = re.match(
            r'^(\d{{4}})-({})-([\w& ]+)-(\d{{3}})-([A-Z][A-Z0-9]?)$'.format(
                '|'.join([x[0] for x in Term.QUARTERNAME_CHOICES])),
            course_id, re.I)
        if not course_parts:
            raise InvalidParamException(
                'invalid course id: {}'.format(course_id))

        course = Course()
        course.year = course_parts.group(1)
        course.quarter = course_parts.group(2).lower()
        course.curriculum = self.curriculum(course_parts.group(3))
        course.number = self.course_number(course_parts.group(4))
        course.section = self.course_section(course_parts.group(5))
        return course

    def curriculum(self, curriculum):
        if not curriculum:
            raise MissingParamException('missing curriculum')

        if not re.match(r'^[a-z \&]{2,}$', curriculum, re.I):
            raise InvalidParamException(
                'Invalid Curriculum: {}'.format(curriculum))

        return curriculum.upper()

    def course_number(self, course_number):
        if not course_number:
            raise MissingParamException('missing course number')

        if not re.match(r'^\d+$', course_number):
            raise InvalidParamException(
                'Invalid Course Number: {}'.format(course_number))

        return course_number

    def course_section(self, course_section):
        if not course_section:
            raise MissingParamException('missing course section')

        return course_section.upper()

    def panopto_id(self, id):
        if not re.match(r'^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$', id):
            raise InvalidParamException(
                'Invalid Panopto Id: {}'.format(id))

        return id
