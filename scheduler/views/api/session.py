# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from scheduler.views.rest_dispatch import RESTDispatch
from scheduler.exceptions import InvalidParamException, PanoptoUserException
from scheduler.utils import schedule_key
from scheduler.utils.validation import Validation
from scheduler.panopto.folder import get_panopto_folder_creators
from scheduler.dao.panopto.sessions import (
    get_sessions_by_session_ids, update_session_external_id,
    update_session_is_broadcast, move_sessions, delete_sessions,
    get_all_folders_by_external_id, get_folders_list, add_folder,
    update_folder_external_id_with_provider)
from scheduler.dao.panopto.access import (
    get_session_access_details, update_session_is_public,
    grant_users_access_to_folder, revoke_users_access_from_folder)
from scheduler.dao.panopto.user import get_user_by_key
from scheduler.dao.panopto.recorder import (
    schedule_recording, update_recording_time)
from panopto_client import PanoptoAPIException
import json
import logging
import datetime
import pytz
import re


logger = logging.getLogger(__name__)


class Session(RESTDispatch):
    def __init__(self, *args, **kwargs):
        self._audit_log = logging.getLogger('audit')
        super(Session, self).__init__(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        session_id = kwargs.get('session_id')
        if session_id:
            raw_session = get_sessions_by_session_ids([session_id])[0]
            start_utc = raw_session['StartTime'].astimezone(pytz.utc)
            raw_access = get_session_access_details(session_id)
            session = {
                'creator_id': raw_session['CreatorId'],
                'description': raw_session['Description'],
                'duration': raw_session['Duration'],
                'external_id': raw_session['ExternalId'],
                'folder_id': raw_session['FolderId'],
                'folder_name': raw_session['FolderName'],
                'folder_creators': [],
                'id': raw_session['Id'],
                'is_video_url': raw_session['IosVideoUrl'],
                'is_broadcast': raw_session['IsBroadcast'],
                'is_public': raw_access['IsPublic'],
                'is_downloadable': raw_session['IsDownloadable'],
                'name': raw_session['Name'],
                'remote_recorder_ids': raw_session['RemoteRecorderIds'][0],
                'share_page_url': raw_session['SharePageUrl'],
                'start_time': start_utc.isoformat(),
                'state': raw_session['State'],
                'status_message': raw_session['StatusMessage'],
                'thumb_url': raw_session['ThumbUrl'],
                'viewer_url': raw_session['ViewerUrl'],
            }
        else:
            session = {}

        return self.json_response(session)

    def post(self, request, *args, **kwargs):
        try:
            new_session = self._validate_session(request.body)
            session = schedule_recording(
                new_session.get('name'),
                new_session.get('folder_id'),
                new_session.get('is_broadcast'),
                new_session.get('start_time'),
                new_session.get('end_time'),
                new_session.get('recorder_id'))
            if session.ConflictsExist:
                conflict = session.ConflictingSessions[0][0]
                start_time = conflict.StartTime
                end_time = conflict.EndTime
                content = {
                    'conflict_name': conflict.SessionName,
                    'conflict_start': start_time.isoformat(),
                    'conflict_end': end_time.isoformat()
                }
                return self.error_response(
                    409, "Schedule Conflict Exists", content=content)

            session_id = session.SessionIDs[0][0]

            update_session_external_id(
                session_id, new_session.get('external_id'))

            if new_session.get('is_public'):
                update_session_is_public(session_id, True)

            messages = []
            creators = new_session.get('folder_creators')
            if creators and type(creators) is list:
                messages = self._sync_creators(
                    new_session.get('folder_id'), creators)

            self._audit_log.info(
                '{} scheduled {} for {} from {} to {}'.format(
                    request.user, new_session.get('external_id'),
                    new_session.get('uwnetid'),
                    new_session.get('start_time'),
                    new_session.get('end_time')))

            return self.json_response({
                'recording_id': session_id,
                'messages': messages
            })
        except InvalidParamException as ex:
            return self.error_response(400, "{}".format(ex))
        except Exception as ex:
            return self.error_response(
                500, "Unable to save session: {}".format(ex))

    def put(self, request, *args, **kwargs):
        try:
            session_update = self._validate_session(request.body)
            session = get_sessions_by_session_ids(
                session_update.get('recording_id'))[0]

            start_utc = session.StartTime.astimezone(pytz.utc)
            end_utc = start_utc + datetime.timedelta(
                seconds=int(session.Duration))

            session_update_start = self._valid_time(
                session_update.get('start_time'))
            session_update_end = self._valid_time(
                session_update.get('end_time'))

            if not (start_utc.isoformat() == session_update_start and
                    end_utc.isoformat() == session_update_end):
                update_recording_time(
                    session.Id, session_update_start, session_update_end)

            access = get_session_access_details(session.Id)
            if access.IsPublic != session_update.get('is_public'):
                update_session_is_public(
                    session.Id, session_update.get('is_public'))

            if session.IsBroadcast != session_update.get('is_broadcast'):
                update_session_is_broadcast(
                    session.Id, session_update.get('is_broadcast'))

            folder_name = session_update.get('folder_name')
            if session.FolderName != folder_name:
                move_sessions([session.Id], session_update.get('folder_id'))

            messages = []
            creators = session_update.get('folder_creators')
            if creators and type(creators) is list:
                messages = self._sync_creators(
                    session_update.get('folder_id'), creators)

            self._audit_log.info(
                '{} modified {} for {} from {} to {} in {}'.format(
                    request.user,
                    session_update.get('external_id'),
                    session_update.get('uwnetid'),
                    session_update.get('start_time'),
                    session_update.get('end_time'),
                    session_update.get('folder_name')))

            return self.json_response({
                'recording_id': session.Id,
                'messages': messages
            })
        except InvalidParamException as ex:
            return self.error_response(400, "{}".format(ex))
        except Exception as ex:
            return self.error_response(
                500, "Unable to save session: {}".format(ex))

    def delete(self, request, *args, **kwargs):
        try:
            session_id = self._valid_recorder_id(kwargs.get('session_id'))
            # do not permit param tampering
            key = schedule_key(request.GET.get('uwnetid', ''),
                               request.GET.get('name', ''),
                               request.GET.get('eid', ''),
                               request.GET.get('rid', ''),
                               request.GET.get('rstart', ''),
                               request.GET.get('rend', ''))

            if key != request.GET.get("key", None):
                raise InvalidParamException('Invalid Client Key')

            delete_sessions([session_id])
            self._audit_log.info('{} deleted session {}'.format(
                request.user, session_id))
            return self.json_response({
                'deleted_recording_id': session_id
            })
        except InvalidParamException as err:
            return self.error_response(
                400, "Invalid Parameter: {}".format(err))

    def _valid_folder(self, name, external_id):
        try:
            folder_id = Validation().panopto_id(external_id)
            return folder_id
        except InvalidParamException:
            pass

        try:
            if external_id and len(external_id):
                folders = get_all_folders_by_external_id([external_id])
                if folders and len(folders) == 1 and len(folders[0]):
                    return folders[0][0].Id

            folders = get_folders_list(search_query=name)
            if folders and len(folders):
                for folder in folders:
                    if folder.Name == name:
                        folder_id = folder.Id
                        self._set_external_id(folder_id, external_id)
                        return folder_id

            new_folder = add_folder(name)
            if not new_folder:
                raise InvalidParamException(
                    'Cannot add folder: {}'.format(name))

            new_folder_id = new_folder.Id
            self._set_external_id(new_folder_id, external_id)
            return new_folder_id
        except Exception as ex:
            raise InvalidParamException('Cannot add folder: {}'.format(ex))

    def _set_external_id(self, folder_id, external_id):
        if external_id and len(external_id):
            update_folder_external_id_with_provider(
                folder_id, external_id, getattr(
                    settings, 'PANOPTO_API_APP_ID', ''))

    def _validate_session(self, request_body):
        session = {}
        data = json.loads(request_body)

        session['recording_id'] = data.get("recording_id", "")
        session['uwnetid'] = data.get("uwnetid", "")
        session['name'] = self._valid_recording_name(
            data.get("name", "").strip())
        session['external_id'] = self._valid_external_id(
            data.get("external_id", "").strip())
        session['recorder_id'] = self._valid_recorder_id(
            data.get("recorder_id", "").strip())
        session['folder_external_id'] = data.get(
            "folder_external_id", "").strip()

        session['session_id'] = data.get("session_id", "").strip()
        if len(session['session_id']):
            self._valid_external_id(session['session_id'])

        session['is_broadcast'] = self._valid_boolean(
            data.get("is_broadcast", False))
        session['is_public'] = self._valid_boolean(
            data.get("is_public", False))
        session['start_time'] = self._valid_time(
            data.get("start_time", "").strip())
        session['end_time'] = self._valid_time(
            data.get("end_time", "").strip())
        session['folder_name'] = data.get("folder_name", "").strip()
        session['folder_id'] = self._valid_folder(
            session['folder_name'], session['folder_external_id'])
        session['folder_creators'] = data.get("creators", None)

        # do not permit param tamperings
        key = schedule_key(session['uwnetid'], session['name'],
                           session['external_id'], session['recorder_id'],
                           data.get("event_start", "").strip(),
                           data.get("event_end", "").strip())
        if key != data.get("key", ''):
            raise InvalidParamException('Invalid Client Key')

        return session

    def _valid_external_id(self, external_id):
        if external_id and len(external_id):
            return external_id

        raise InvalidParamException('bad external_id')

    def _valid_recorder_id(self, recorder_id):
        if (recorder_id):
            return Validation().panopto_id(recorder_id)

        raise InvalidParamException('missing recorder id')

    def _valid_recording_name(self, name):
        if name and len(name):
            return name

        raise InvalidParamException('bad recording name')

    def _valid_boolean(self, is_broadcast):
        if not (is_broadcast is None or type(is_broadcast) == bool):
            raise InvalidParamException('bad broadcast flag')

        return is_broadcast

    def _valid_time(self, time):
        if time and len(time):
            return time

        raise InvalidParamException('bad time value')

    def _sync_creators(self, folder_id, folder_creators):
        messages = []
        new_creator_ids = []
        deleted_creator_ids = []
        current_creators = get_panopto_folder_creators(folder_id)
        for creator in folder_creators:
            if creator not in current_creators:
                try:
                    new_creator_ids.append(self._get_panopto_user_id(creator))
                except PanoptoUserException as ex:
                    messages.append('Invalid UWNetId {}'.format(creator))

        for creator in current_creators:
            if creator not in folder_creators:
                try:
                    deleted_creator_ids.append(
                        self._get_panopto_user_id(creator))
                except PanoptoUserException as ex:
                    messages.append('Invalid UWNetId {}'.format(creator))

        if len(new_creator_ids):
            try:
                grant_users_access_to_folder(
                    folder_id, new_creator_ids, 'Creator')
            except PanoptoAPIException as ex:
                match = re.match(r'.*Server raised fault: \'(.+)\'$', str(ex))
                messages.append('{}: {}'.format(creator, match.group(1) if (
                    match) else str(ex)))

        if len(deleted_creator_ids):
            try:
                revoke_users_access_from_folder(
                    folder_id, deleted_creator_ids, 'Creator')
            except PanoptoAPIException as ex:
                match = re.match(r'.*Server raised fault: \'(.+)\'$', str(ex))
                messages.append('{}: {}'.format(creator, match.group(1) if (
                    match) else str(ex)))

        return messages

    def _get_panopto_user_id(self, netid):
        key = r'{}\{}'.format(
            getattr(settings, 'PANOPTO_API_APP_ID', ''), netid)
        user = get_user_by_key(key)
        if (not user or
                user['UserId'] == '00000000-0000-0000-0000-000000000000'):
            raise PanoptoUserException(
                'Unprovisioned UWNetId: {}'.format(netid))

        return user['UserId']


class SessionPublic(RESTDispatch):
    def __init__(self):
        self._audit_log = logging.getLogger('audit')

    def get(self, request, *args, **kwargs):
        session_id = kwargs.get('session_id')
        if session_id:
            raw_access = get_session_access_details(session_id)
            access = {
                'is_public': raw_access['IsPublic']
            }
        else:
            access = {}

        return self.json_response(access)

    def put(self, request, *args, **kwargs):
        try:
            session_id = kwargs.get('session_id')
            data = json.loads(request.body)
            is_public = self._valid_boolean(data.get("is_public", False),
                                            'bad public flag')
            update_session_is_public(session_id, is_public)
            self._audit_log.info('{} set {} public access to {}'.format(
                request.user, session_id, is_public))

            return self.json_response({
                'recording_id': session_id
            })
        except InvalidParamException as ex:
            return self.error_response(400, "{}".format(ex))
        except Exception as ex:
            return self.error_response(
                500, "Unable to save session: {}".format(ex))

    def _valid_boolean(self, v, errstr):
        if not (v is None or type(v) == bool):
            raise InvalidParamException(errstr)

        return v


class SessionBroadcast(RESTDispatch):
    def __init__(self):
        self._audit_log = logging.getLogger('audit')

    def get(self, request, *args, **kwargs):
        session_id = kwargs.get('session_id')
        if session_id:
            raw_session = get_sessions_by_session_ids([session_id])[0]
            broadcast = {
                'is_broadcast': raw_session['IsBroadcast'],
            }
        else:
            broadcast = {}

        return self.json_response(broadcast)

    def put(self, request, *args, **kwargs):
        try:
            session_id = kwargs.get('session_id')
            data = json.loads(request.body)
            is_broadcast = self._valid_boolean(
                data.get("is_broadcast", False), 'bad broadcast flag')
            update_session_is_broadcast(session_id, is_broadcast)
            self._audit_log.info('{} set {} broadcast to {}'.format(
                request.user, session_id, is_broadcast))

            return self.json_response({
                'recording_id': session_id
            })
        except InvalidParamException as ex:
            return self.error_response(400, "{}".format(ex))
        except Exception as ex:
            return self.error_response(
                500, "Unable to save session: {}".format(ex))

    def _valid_boolean(self, v, errstr):
        if not (v is None or type(v) == bool):
            raise InvalidParamException(errstr)

        return v


class SessionRecordingTime(RESTDispatch):
    def __init__(self):
        self._audit_log = logging.getLogger('audit')

    def get(self, request, *args, **kwargs):
        session_id = kwargs.get('session_id')
        if session_id:
            raw_session = get_sessions_by_session_ids([session_id])[0]
            start_utc = raw_session.StartTime.astimezone(pytz.utc)
            end_utc = start_utc + datetime.timedelta(
                seconds=int(raw_session.Duration))
            recording_time = {
                'start': start_utc.isoformat(),
                'end': end_utc.isoformat()
            }
        else:
            recording_time = {}

        return self.json_response(recording_time)

    def put(self, request, *args, **kwargs):
        try:
            session_id = kwargs.get('session_id')
            data = json.loads(request.body)
            start_time = self._valid_time(data.get("start", "").strip())
            end_time = self._valid_time(data.get("end", "").strip())

            update_recording_time(session_id, start_time, end_time)

            self._audit_log.info('{} set {} start/stop to {} and {}'.format(
                request.user, session_id, start_time, end_time))

            return self.json_response({
                'recording_id': session_id
            })
        except InvalidParamException as ex:
            return self.error_response(400, "{}".format(ex))
        except Exception as ex:
            return self.error_response(
                500, "Unable to save session: {}".format(ex))

    def _valid_time(self, time):
        if time and len(time):
            return time

        raise InvalidParamException('bad time value')
