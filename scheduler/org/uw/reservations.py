# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from scheduler.reservations.r25 import R25Reservations


class Reservations(R25Reservations):
    @property
    def instruction_profiles(self):
        """R25 profile names indicating instructor is likely present"""
        return ['lecture', 'seminar', 'quiz']

    @property
    def course_profiles(self):
        """R25 profile names indicating course and/or instruction related"""
        return self.instruction_profiles + ['lab', 'final']
