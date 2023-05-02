# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from panopto_client.session import SessionManagement


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


def get_folders_list(*args, **kwargs):
    return session_api.getFoldersList(*args, **kwargs)


def get_all_folders_by_external_id(external_ids):
    return session_api.getAllFoldersByExternalId(external_ids)


def add_folder(name):
    return session_api.addFolder(name)


def update_folder_external_id_with_provider(folder_id, external_id, provider):
    return session_api.updateFolderExternalIdWithProvider(
        folder_id, external_id, provider)
