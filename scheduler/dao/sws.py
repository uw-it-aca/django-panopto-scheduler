# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from uw_sws.section import get_section_by_label, get_section_by_url
from uw_sws.models import SWS_SECTION_LABEL
from scheduler.utils import timer


@timer
def get_sws_section_for_course(course):
    label = SWS_SECTION_LABEL.format(
        year=course.year, quarter=course.quarter, curr_abbr=course.curriculum,
        course_num=course.number, section_id=course.section_id)
    return get_section_by_label(
        label, include_instructor_not_on_time_schedule=False)


@timer
def get_sws_section_by_url(url):
    return get_section_by_url(url)
