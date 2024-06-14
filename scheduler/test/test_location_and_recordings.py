# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from django.test.utils import override_settings
from scheduler.schedule import course_location_and_recordings
import logging


# silence suds debugging telemetry
logging.getLogger('suds').setLevel(logging.ERROR)

course_test_override = override_settings(
    USER_MODULE='scheduler.org.uw.user',
    COURSES_MODULE='scheduler.org.uw.course',
    RESERVATIONS_MODULE='scheduler.org.uw.reservations',
)


@course_test_override
class TestCourseLocationAndRecordings(TestCase):
    def test_course_location_and_recordings(self):
        events = course_location_and_recordings('2015-autumn-PSYCH-101-A')
        self.assertEqual(len(events), 53)
