# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from scheduler.reservations.r25 import R25Reservations


class Reservations(R25Reservations):
    @property
    def instruction_profiles(self):
        return ['lecture', 'seminar', 'quiz']

    @property
    def course_profiles(self):
        return self.instruction_profiles + ['lab', 'final']

    def profile_name(self, profile):
        return profile.split()[-1].lower() if profile else ''
