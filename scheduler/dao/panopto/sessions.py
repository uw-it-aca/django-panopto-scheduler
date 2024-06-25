# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from panopto_client.session import SessionManagement
from panopto_client import PanoptoAPIException
from scheduler.utils import panopto_app_id


session_api = SessionManagement()


def get_sessions_by_external_ids(external_ids):
    sessions = session_api.getSessionsByExternalId(external_ids)
    return sessions.Session if (sessions and 'Session' in sessions and
                                len(sessions.Session)) else None


def get_sessions_by_session_ids(session_ids):
    sessions = session_api.getSessionsById(session_ids)
    return sessions.Session if (sessions and 'Session' in sessions and
                                len(sessions.Session)) else None


def update_session_external_id(session_id, external_id):
    return session_api.updateSessionExternalId(session_id, external_id)


def update_session_is_broadcast(session_id, is_broadcast):
    return session_api.updateSessionIsBroadcast(session_id, is_broadcast)


def move_sessions(session_ids, folder_id):
    return session_api.moveSessions(session_ids, folder_id)


def delete_sessions(session_ids):
    return session_api.deleteSessions(session_ids)


def get_folders_by_id(folder_ids):
    try:
        return session_api.getFoldersById(folder_ids)
    except PanoptoAPIException as ex:
        if str(ex).find("was not found") > 0:
            raise PanoptoFolderDoesNotExist(ex)
        else:
            raise ex


def get_folders_with_external_context_list(*args, **kwargs):
    return session_api.getFoldersWithExternalContextList(*args, **kwargs)


def get_folders_list(*args, **kwargs):
    return session_api.getFoldersList(*args, **kwargs)


def get_all_folders_with_external_context_by_external_id(
        external_ids, providers=None):
    if not providers:
        providers = [panopto_app_id()]

    return session_api.getAllFoldersWithExternalContextByExternalId(
        external_ids, providers)


def get_all_folders_by_external_id(external_ids):
    return session_api.getAllFoldersByExternalId(external_ids)


def add_folder(name, parent_id=None, is_public=False):
    return session_api.addFolder(name, parent_id, is_public)


def provision_external_course(course_name, external_id):
    return session_api.provisionExternalCourse(course_name, external_id)


def update_folder_external_id_with_provider(folder_id, external_id, provider):
    return session_api.updateFolderExternalIdWithProvider(
        folder_id, external_id, provider)
