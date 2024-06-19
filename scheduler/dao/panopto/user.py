# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from panopto_client.user import UserManagement
from scheduler.utils import timer


user_api = UserManagement()


@timer
def get_users_from_guids(guids):
    return user_api.getUsers(guids)


@timer
def get_user_by_key(key):
    return user_api.getUserByKey(key)
