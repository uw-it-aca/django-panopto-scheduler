# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from panopto_client.access import AccessManagement


access_api = AccessManagement()


def get_session_access_details(session_id):
    return access_api.getSessionAccessDetails(session_id)


def get_folder_access_details(folder_id):
    return access_api.getFolderAccessDetails(folder_id)


def update_session_is_public(session_id, is_public):
    return access_api.updateSessionIsPublic(session_id, is_public)


def grant_users_access_to_folder(folder_id, creator_ids, access_type):
    return access_api.grantUsersAccessToFolder(
        folder_id, creator_ids, access_type)


def revoke_users_access_from_folder(folder_id, creator_ids, access_type):
    return access_api.revokeUsersAccessFromFolder(
        folder_id, creator_ids, access_type)
