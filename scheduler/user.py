# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
from scheduler.utils.loader import load_class_from_module_setting


USER_MODULE_SETTING = 'USER_MODULE'


class User(object):
    """Indirection class used to load campus-specific Course class"""
    def __new__(self, *args, **kwargs):
        return load_class_from_module_setting(
            USER_MODULE_SETTING, 'User', *args, **kwargs)


class BaseUser(ABC):
    """Base class defines methods necessary for pantoto and campus
       to reference a common user identity
    """

    @abstractmethod
    def validate_login_ids(self, login_ids):
        """From list of strings containing potential login ids,
           return each validated login id, or string corresponding
           to an error condition.
        """
        pass

    @abstractmethod
    def validate_login_id(self, login_id):
        """Parse login id from email address as necessary"""
        pass
