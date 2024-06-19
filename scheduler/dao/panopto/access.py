# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from panopto_client.access import AccessManagement
from scheduler.utils import timer


access_api = AccessManagement()


@timer
def get_session_access_details(session_id):
    return access_api.getSessionAccessDetails(session_id)


@timer
def get_folder_access_details(folder_id):
    return access_api.getFolderAccessDetails(folder_id)


@timer
def update_session_is_public(session_id, is_public):
    return access_api.updateSessionIsPublic(session_id, is_public)


@timer
def grant_users_access_to_folder(folder_id, creator_ids, access_type):
    return access_api.grantUsersAccessToFolder(
        folder_id, creator_ids, access_type)


@timer
def revoke_users_access_from_folder(folder_id, creator_ids, access_type):
    return access_api.revokeUsersAccessFromFolder(
        folder_id, creator_ids, access_type)
