# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

#
# Implements Reservations access and model instantiation for
# CollegeNET r25 Facility/Resource Reservations
#

from scheduler.reservations import BaseReservations
from scheduler.models import Event, Reservation
from scheduler.dao.r25 import (
    get_event_by_course, get_reservations_by_search_params,
    get_spaces, get_space_by_id)


class R25Reservations(BaseReservations):
    def get_event_by_course(self, course):
        """
        """
        r25 = get_event_by_course(course)
        event = Event(is_crosslisted=(len(r25.binding_reservations) > 0))
        event.reservations = []
        for r in r25.reservations:
            event.reservations.append(self._reservation_from_r25(r))

        return event

    def get_reservations_by_search_params(self, search):
        reservations = []
        for r25 in get_reservations_by_search_params(search):
            reservations.append(self._reservation_from_r25(r25))

        return reservations

    def _reservation_from_r25(self, r25):
        """Map r25 reservation resourse into a Reservation model"""
        return Reservation(
            event_name=r25.event_name,
            profile_name=self.profile_name(r25.profile_name),
            contact_name=r25.contact_name,
            contact_email=r25.contact_email or '',
            space_id=str(r25.space_reservation.space_id) if (
                r25.space_reservation) else None,
            space_name=r25.space_reservation.name if (
                r25.space_reservation) else None,
            space_formal_name=r25.space_reservation.formal_name if (
                r25.space_reservation) else None,
            is_course=(self.profile_name(r25.profile_name)
                       in self.course_profiles),
            is_instruction=(self.profile_name(r25.profile_name)
                            in self.instruction_profiles),
            start_datetime=r25.start_datetime,
            end_datetime=r25.end_datetime)

    @property
    def instruction_profiles(self):
        """R25 profile names indicating instructor is likely present"""
        return []

    @property
    def course_profiles(self):
        """R25 profile names indicating course and/or instruction related"""
        return []

    def profile_name(self, profile):
        return profile or ''

    def get_space_by_id(self, space_id):
        return get_space_by_id(space_id)

    def get_spaces(self, *args, **kwargs):
        return get_spaces(*args, **kwargs)
