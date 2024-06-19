# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from panopto_client.session import SessionManagement
from scheduler.utils import panopto_app_id
from scheduler.utils import timer


session_api = SessionManagement()


@timer
def get_sessions_by_external_ids(external_ids):
    sessions = session_api.getSessionsByExternalId(external_ids)
    return sessions.Session if (sessions and 'Session' in sessions and
                                len(sessions.Session)) else None


@timer
def get_sessions_by_session_ids(session_ids):
    sessions = session_api.getSessionsById(session_ids)
    return sessions.Session if (sessions and 'Session' in sessions and
                                len(sessions.Session)) else None


@timer
def update_session_external_id(session_id, external_id):
    return session_api.updateSessionExternalId(session_id, external_id)


@timer
def update_session_is_broadcast(session_id, is_broadcast):
    return session_api.updateSessionIsBroadcast(session_id, is_broadcast)


@timer
def move_sessions(session_ids, folder_id):
    return session_api.moveSessions(session_ids, folder_id)


@timer
def delete_sessions(session_ids):
    return session_api.deleteSessions(session_ids)


@timer
def get_folders_list(*args, **kwargs):
    return session_api.getFoldersList(*args, **kwargs)


@timer
def get_all_folders_with_external_context_list(external_ids, providers=None):
    if not providers:
        providers = [panopto_app_id()]

    return session_api.getAllFoldersWithExternalContextByExternalId(
        external_ids, providers)


@timer
def get_all_folders_by_external_id(external_ids):
    return session_api.getAllFoldersByExternalId(external_ids)


@timer
def add_folder(name):
    return session_api.addFolder(name)


@timer
def provision_external_course(course_name, external_id):
    return session_api.provisionExternalCourse(course_name, external_id)


@timer
def update_folder_external_id_with_provider(folder_id, external_id, provider):
    return session_api.updateFolderExternalIdWithProvider(
        folder_id, external_id, provider)
