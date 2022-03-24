# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

import logging


class UserFilter(logging.Filter):
    """ Add user information to each log entry. """

    def filter(self, record):
        from userservice.user import UserService

        user_service = UserService()
        record.user = user_service.get_original_user() or "-"
        record.actas = (user_service.get_user() or "-").lower()
        return True


class InfoFilter(logging.Filter):
    """ Limits log level to INFO only. """

    def filter(self, record):
        return record.levelname == "INFO"
