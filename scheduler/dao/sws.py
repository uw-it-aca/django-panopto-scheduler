# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from uw_sws.section import get_section_by_label, get_section_by_url


def get_sws_section_for_course(course):
    return get_section_by_label(
        course.sws_course_label(),
        include_instructor_not_on_time_schedule=False)


def get_sws_section_by_url(url):
    return get_section_by_url(url)
