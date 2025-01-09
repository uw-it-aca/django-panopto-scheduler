# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from uw_r25.events import get_event_by_alien_id
from uw_r25.reservations import get_reservations
from uw_r25.spaces import get_space_by_id as r25_space_by_id
from uw_r25.spaces import get_spaces as r25_get_spaces
from scheduler.exceptions import CourseReservationsException


def get_event_by_course(course):
    """"""
    reservation_uid = course.reservation_uid()
    event = get_event_by_alien_id(reservation_uid)

    if not event:
        raise CourseReservationsException(
            "No course events found for {}".format(reservation_uid))

    return event


def get_reservations_by_search_params(search):
    """"""
    return get_reservations(**search)


def get_space_by_id(id):
    return r25_space_by_id(id)


def get_spaces(*args, **kwargs):
    return r25_get_spaces(*args, **kwargs)
