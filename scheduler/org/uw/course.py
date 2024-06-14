# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from scheduler.course import BaseCourse
from scheduler.models import Curriculum
from scheduler.utils import local_ymd_from_utc_date_string
from scheduler.dao.canvas import get_course_by_sis_id
from scheduler.dao.panopto.sessions import (
    get_all_folders_with_external_context_list, provision_external_course)
from scheduler.dao.sws import (
    get_sws_section_for_course, get_sws_section_by_url)
from scheduler.exceptions import (
    MissingParamException, InvalidParamException, PanoptoFolderDoesNotExist)

from restclients_core.exceptions import DataFailureException
from dateutil import parser
from nameparser import HumanName
import logging
import re


logger = logging.getLogger(__name__)


class Course(BaseCourse):
    year = ""
    quarter = ""
    curriculum = ""
    number = ""
    section = ""
    external_id = ""
    canvas_course_id = None
    UW_CAMPUS = ['seattle', 'bothell', 'tacoma']
    UW_TERMS = ['spring', 'summer', 'autumn', 'winter']

    def __init__(self, courseId):
        if not courseId:
            raise MissingParamException('missing course id')

        course_parts = re.match(
            r'^(\d{{4}})-({})-([\w& ]+)-(\d{{3}})-([A-Z][A-Z0-9]?)$'.format(
                '|'.join(self.UW_TERMS)), courseId, re.I)

        if not course_parts:
            raise InvalidParamException(
                'invalid course id: {}'.format(courseId))

        self.year = course_parts.group(1)
        self.quarter = course_parts.group(2).lower()
        self.curriculum = self._is_curriculum(course_parts.group(3))
        self.number = self._is_course_number(course_parts.group(4))
        self.section = self._is_course_section(course_parts.group(5))

    def _is_curriculum(self, curriculum):
        if not curriculum:
            raise MissingParamException('missing curriculum')

        if not re.match(r'^[a-z \&]{2,}$', curriculum, re.I):
            raise InvalidParamException(
                'Invalid Curriculum: {}'.format(curriculum))

        return curriculum.upper()

    def _is_course_number(self, course_number):
        if not course_number:
            raise MissingParamException('missing course number')

        if not re.match(r'^\d+$', course_number):
            raise InvalidParamException(
                'Invalid Course Number: {}'.format(course_number))

        return course_number

    def _is_course_section(self, course_section):
        if not course_section:
            raise MissingParamException('missing course section')

        return course_section.upper()

    def reservation_uid(self):
        # OLD: r25 alien_id: 2014-4 0-MATH 124 A
        # NEW: r25live alien_uid: LYNX-EV-104-20232-PHYS114A
        return "LYNX-EV-104-{}{}-{}{}{}".format(
            self.year, self._quarter_ordinal(),
            self.curriculum.replace(' ', ''),
            self.number, self.section)

    def canvas_sis_id(self):
        return "{}".format('-'.join([
            self.year, self.quarter, self.curriculum,
            self.number, self.section]))

    def panopto_course_external_id(self, start_datetime):
        # session_external_id: 2014-autumn-BIOL-404-A-2014-10-27
        start_dt = parser.parse(start_datetime)
        start_date = start_dt.strftime('%Y-%m-%d')
        return "{}-{}-{}-{}-{}-{}".format(
            self.year, self.quarter, self.curriculum,
            self.number, self.section, start_date)

    def canvas_course(self):
        if self.canvas_course_id is None:
            try:
                return get_course_by_sis_id(self.canvas_sis_id())
            except DataFailureException as ex:
                raise DataFailureException(
                    ex.url, 404 if ex.status == 404 else 424,
                    "course_id fetch: {}".format(ex))

        return self.canvas_course_id

    def panopto_course_folder(self):
        canvas_course = self.canvas_course()
        try:
            panopto_folder = self._panopto_folder_from_course_id(
                str(canvas_course.course_id))
        except PanoptoFolderDoesNotExist:
            panopto_folder = self._create_panopto_folder(canvas_course)

        return {
            'name': panopto_folder.Name,
            'id': panopto_folder.Id
        }

    def _panopto_folder_from_course_id(self, course_id):
        if course_id:
            folders = get_all_folders_with_external_context_list([course_id])
            if folders:
                if len(folders) == 1:
                    if len(folders[0]) == 1:
                        return folders[0][0]
                    else:
                        self._bad_folder_response(len(folders[0]), course_id)
                else:
                    self._bad_folder_response(len(folders), course_id)

        raise PanoptoFolderDoesNotExist()

    def _bad_folder_response(self, folder_count, course_id):
        message = 'Unexpected folder count {} for {}'.format(
            folder_count, course_id)
        logger.error(message)
        raise DataFailureException("", 424, message)

    def _create_panopto_folder(self, canvas_course):
        try:
            folder =  provision_external_course(
                self.panopto_folder_name(canvas_course.name),
                str(canvas_course.course_id))
            if folder:
                return folder

            raise DataFailureException('', 424, 'folder provision failed')
        except DataFailureException as ex:
            raise DataFailureException(
                ex.url, 424, "folder provision: {}".format(ex))

    def panopto_folder_name(self, course_name):
        return "{} {} - ".format(
            self.quarter.capitalize(), self.year, course_name)

    def panopto_course_session(self, start_datetime):
        name = "{} {} {} - {}".format(
            self.curriculum, self.number, self.section,
            local_ymd_from_utc_date_string(start_datetime))
        external_id = self.panopto_course_external_id(
            local_ymd_from_utc_date_string(start_datetime))
        return (name, external_id)

    def course_event_title_and_contact(self):
        try:
            section = get_sws_section_for_course(self)
            meeting = section.meetings[0] if hasattr(
                section, 'meetings') and len(section.meetings) else None
            instructor = meeting.instructors[0] if hasattr(
                meeting, 'instructors') and len(meeting.instructors) else None
            first_name = instructor.first_name if hasattr(
                instructor, 'first_name') else ''
            surname = instructor.surname if hasattr(
                instructor, 'surname') else ''
            uwnetid = instructor.uwnetid if hasattr(
                instructor, 'uwnetid') else ''
            email = instructor.email1 if hasattr(
                instructor, 'email1') else ''
            name = HumanName(' '.join([first_name, surname]))
            name.capitalize()
        except DataFailureException as err:
            if err.status == 404:
                section = None
                name = None
                email = None
                uwnetid = None
            else:
                raise

        return {
            'title_long': section.course_title_long if section else '',
            'name': '{} {}'.format(name.first, name.last) if name else '',
            'loginid': uwnetid if uwnetid else '',
            'email': email if (
                email and len(email)) else "{}@uw.edu".format(
                    uwnetid if uwnetid else '')
        }

    def get_crosslisted_course(self):
        # default to Canvas course that SIS provisioning selects
        # for student sections
        section = get_sws_section_for_course(self)
        if not section.is_withdrawn and len(section.joint_section_urls):
            joint_course_ids = [self.canvas_sis_id()]
            for url in section.joint_section_urls:
                try:
                    joint_section = get_sws_section_by_url(url)
                    if not joint_section.is_withdrawn:
                        joint_course_id = joint_section.canvas_course_sis_id()
                        joint_course_ids.append(joint_course_id)
                        c = Course(joint_course_id)
                        joint_course_ids.append(c.canvas_sis_id())
                except Exception:
                    continue

            if len(joint_course_ids):
                joint_course_ids.sort()
                return Course(joint_course_ids[0])

        return self

    def _quarter_ordinal(self):
        quarters = ['winter', 'spring', 'summer', 'autumn']
        return quarters.index(self.quarter.lower()) + 1

    def _campus_ordinal(self):
        try:
            return Curriculum.objects.get(
                curriculum_abbr=self.curriculum).campus_code
        except Curriculum.DoesNotExist:
            section = get_sws_section_for_course(self)
            campus_code = self.UW_CAMPUS.index(section.course_campus.lower())
            curriculum = Curriculum(curriculum_abbr=self.curriculum,
                                    campus_code=campus_code)
            curriculum.save()
            return campus_code
