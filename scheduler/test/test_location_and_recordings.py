# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from scheduler.utils import course_location_and_recordings
from scheduler.utils.validation import Validation
import logging


# silence suds debugging telemetry
logging.getLogger('suds').setLevel(logging.ERROR)


class TestCourseLocationAndRecordings(TestCase):
    def test_course_location_and_recordings(self):
        course = Validation().course_id('2015-autumn-PSYCH-101-A')
        events = course_location_and_recordings(course)

        self.assertEqual(len(events), 53)
