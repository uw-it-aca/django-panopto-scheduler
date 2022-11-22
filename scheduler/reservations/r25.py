# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

#  
#
#

from scheduler.reservations import BaseReservations
from scheduler.dao.r25 import (
    get_event_by_course, get_reservations_by_search_params,
    get_spaces, get_space_by_id)


class R25Reservations(BaseReservations):
    def get_event_by_course(self, course):
        """
        """
        return get_event_by_course(course)

    def get_reservations_by_search_params(self, search):
        return get_reservations_by_search_params(search)

    def get_space_by_id(self, space_id):
        """
        """
        return get_space_by_id(space_id)

    def get_spaces(self, *args):
        return get_spaces(args)
