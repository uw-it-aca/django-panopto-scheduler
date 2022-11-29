# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

#
# Reservations reflect the course meeting time and location as they
# are represented in the Facilities Scheduling System
#

from abc import ABC, abstractmethod
from scheduler.utils.loader import load_class_from_module_setting


RESERVATIONS_MODULE = 'RESERVATIONS_MODULE'


class Reservations(object):
    """Indirection class used to load campus-specific meeting schedule"""
    def __new__(self, *args, **kwargs):
        return load_class_from_module_setting(
            RESERVATIONS_MODULE, 'Reservations', *args, **kwargs)


class BaseReservations(ABC):
    """Base class defines methods necessary for an event and associated
       reservations scheduling.
    """

    @abstractmethod
    def get_event_by_course(self, course):
        """Return facilities schedule for provided course"""
        pass

    @abstractmethod
    def get_reservations_by_search_params(self, search):
        """Return facilities schedule for provided search criteria"""
        pass

    @abstractmethod
    def get_space_by_id(self, space_id):
        """Return specific reservable space by provided id"""
        pass

    @abstractmethod
    def get_spaces(self, *args, **kwargs):
        """Return list of reservable spaces based on supplied filter"""
        pass
