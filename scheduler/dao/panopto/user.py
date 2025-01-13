# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from panopto_client.user import UserManagement


user_api = UserManagement()


def get_users_from_guids(guids):
    return user_api.getUsers(guids)


def get_user_by_key(key):
    return user_api.getUserByKey(key)
