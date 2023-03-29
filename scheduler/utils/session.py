# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from panopto_client.session import SessionManagement


def get_sessions_by_external_ids(external_ids):
    api = SessionManagement()
    sessions = api.getSessionsByExternalId(external_ids)
    return sessions.Session if (sessions and 'Session' in sessions and
                                len(sessions.Session)) else None


def get_sessions_by_session_ids(session_ids):
    api = SessionManagement()
    sessions = api.getSessionsById(session_ids)
    return sessions.Session if (sessions and 'Session' in sessions and
                                len(sessions.Session)) else None
