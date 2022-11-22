# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

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
        pass

    @abstractmethod
    def get_reservations_by_search_params(self, search):
        pass

    @abstractmethod
    def get_space_by_id(self, space_id):
        """
        """
        pass

    @abstractmethod
    def get_spaces(self):
        """
        space_id:  (or some token unique to the event's space/location)
        name: short name for the event's space/location
        formal_name: long name for event's space/location
        """
        pass
