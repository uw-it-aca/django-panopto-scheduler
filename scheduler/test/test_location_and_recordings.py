# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from django.test.utils import override_settings
from scheduler.course import Course
from scheduler.schedule import course_location_and_recordings
import logging


# silence suds debugging telemetry
logging.getLogger('suds').setLevel(logging.ERROR)

course_test_override = override_settings(
    CAMPUS_COURSES_MODULE='scheduler.course.uw'
)


@course_test_override
class TestCourseLocationAndRecordings(TestCase):
    def test_course_location_and_recordings(self):
        course = Course('2015-autumn-PSYCH-101-A')
        events = course_location_and_recordings(course)

        self.assertEqual(len(events), 53)
