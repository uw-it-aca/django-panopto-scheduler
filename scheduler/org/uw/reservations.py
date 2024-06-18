# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from scheduler.reservations.r25 import R25Reservations
import logging
import re


logger = logging.getLogger(__name__)


class Reservations(R25Reservations):
    """
    University of Washington reservation profile definitions

    The general profile_name format is "MWF 1050-1150 LC 06/17"
    where:
       - first field holds course meeting days
       - second field holds course meeting start and end time
       - third field is type of course, which could be:
            - LC: lecture
            - SM: seminar
            - QZ: quiz
            - LB: Lab
            - ST: Studio
            - CL: clinic, usually off site or departmental clinic spaces
            - CK: clerkship
            - CO: conference
            - PR: practicum
       - fourth field is course start date
    """

    profile_name_re = re.compile(r'^(?P<meeting_day>[A-Z]+)\s'
                                 r'(?P<start_time>\d{4})-(?P<end_time>\d{4})\s'
                                 r'(?P<course_type>[A-Z]{2})\s'
                                 r'(?P<start_date>\d{2}/\d{2})$')

    @property
    def instruction_profiles(self):
        return ['LC', 'SM', 'QZ']

    @property
    def course_profiles(self):
        return self.instruction_profiles + ['LB']

    def course_type(self, profile):
        try:
            fields = self.profile_name_re.match(profile.upper())
            return fields.group('course_type')
        except AttributeError:
            pass

        logger.info('Unknown reservation profile: {}'.format(profile))
        return ''
