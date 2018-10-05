from django.conf import settings
from scheduler.views.rest_dispatch import RESTDispatch
from scheduler.views.api.exceptions import MissingParamException, \
    InvalidParamException
from scheduler.utils import PanoptoAPIException
from scheduler.utils import course_event_key
from scheduler.utils import get_panopto_folder_creators
from scheduler.utils.validation import Validation
from panopto_client.session import SessionManagement
from panopto_client.access import AccessManagement
from panopto_client.user import UserManagement
from panopto_client.remote_recorder import RemoteRecorderManagement
from dateutil import parser, tz
import json
import logging
import datetime
import pytz
import re


logger = logging.getLogger(__name__)


class PanoptoUserException(Exception):
    pass


class Session(RESTDispatch):
    def __init__(self):
        self._audit_log = logging.getLogger('audit')

    def _init_apis(self):
        self._session_api = SessionManagement()
        self._recorder_api = RemoteRecorderManagement()
        self._access_api = AccessManagement()
        self._user_api = UserManagement()

    def get(self, request, *args, **kwargs):
        session_id = kwargs.get('session_id')
        if session_id:
            self._init_apis()
            raw_session = self._session_api.getSessionsById(
                [session_id])[0][0]
            raw_access = self._access_api.getSessionAccessDetails(
                session_id)
            start_utc = pytz.utc.localize(
                raw_session['StartTime']).astimezone(tz.tzutc())
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
                'remote_recorder_ids': raw_session['RemoteRecorderIds'].get(
                    'guid', None),
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
            self._init_apis()
            new_session = self._validate_session(request.body)
            session = self._recorder_api.scheduleRecording(
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

            self._session_api.updateSessionExternalId(
                session_id, new_session.get('external_id'))

            if new_session.get('is_public'):
                self._access_api.updateSessionIsPublic(session_id, True)

            messages = []
            creators = new_session.get('folder_creators')
            if creators and type(creators) is list:
                messages = self._sync_creators(
                    new_session.get('folder_id'), creators)

            self._audit_log.info('%s scheduled %s for %s from %s to %s' % (
                request.user, new_session.get('external_id'),
                new_session.get('uwnetid'), new_session.get('start_time'),
                new_session.get('end_time')))

            return self.json_response({
                'recording_id': session_id,
                'messages': messages
            })
        except InvalidParamException as ex:
            return self.error_response(400, "%s" % ex)
        except Exception as ex:
            return self.error_response(500, "Unable to save session: %s" % ex)

    def put(self, request, *args, **kwargs):
        try:
            self._init_apis()
            session_update = self._validate_session(request.body)
            session = self._session_api.getSessionsById(
                session_update.get('recording_id'))[0][0]

            start_utc = session.StartTime.astimezone(pytz.utc)
            end_utc = start_utc + datetime.timedelta(
                seconds=int(session.Duration))

            session_update_start = self._valid_time(
                session_update.get('start_time'))
            session_update_end = self._valid_time(
                session_update.get('end_time'))

            if not (start_utc.isoformat() == session_update_start and
                    end_utc.isoformat() == session_update_end):
                self._recorder_api.updateRecordingTime(
                    session.Id, session_update_start, session_update_end)

            access = self._access_api.getSessionAccessDetails(session.Id)
            if access.IsPublic != session_update.get('is_public'):
                self._access_api.updateSessionIsPublic(
                    session.Id, session_update.get('is_public'))

            if session.IsBroadcast != session_update.get('is_broadcast'):
                self._session_api.updateSessionIsBroadcast(
                    session.Id, session_update.get('is_broadcast'))

            folder_name = session_update.get('folder_name')
            if session.FolderName != folder_name:
                self._session_api.moveSessions(
                    [session.Id], session_update.get('folder_id'))

            messages = []
            creators = session_update.get('folder_creators')
            if creators and type(creators) is list:
                messages = self._sync_creators(
                    session_update.get('folder_id'), creators)

            self._audit_log.info(
                '%s modified %s for %s from %s to %s in %s' % (
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
            return self.error_response(400, "%s" % ex)
        except Exception as ex:
            return self.error_response(500, "Unable to save session: %s" % ex)

    def delete(self, request, *args, **kwargs):
        try:
            self._init_apis()
            session_id = self._valid_recorder_id(kwargs.get('session_id'))
            # do not permit param tampering
            key = course_event_key(request.GET.get('uwnetid', ''),
                                   request.GET.get('name', ''),
                                   request.GET.get('eid', ''),
                                   request.GET.get('rid', ''),
                                   request.GET.get('rstart', ''),
                                   request.GET.get('rend', ''))

            if key != request.GET.get("key", None):
                raise InvalidParamException('Invalid Client Key')

            self._session_api.deleteSessions([session_id])
            self._audit_log.info('%s deleted session %s' %
                                 (request.user, session_id))
            return self.json_response({
                'deleted_recording_id': session_id
            })
        except InvalidParamException as err:
            return self.error_response(400, "Invalid Parameter: %s" % err)

    def _valid_folder(self, name, external_id):
        try:
            folder_id = Validation().panopto_id(external_id)
            return folder_id
        except InvalidParamException:
            pass

        try:
            if external_id and len(external_id):
                folders = self._session_api.getAllFoldersByExternalId(
                    [external_id])
                if folders and len(folders) == 1 and len(folders[0]):
                    return folders[0][0].Id

            folders = self._session_api.getFoldersList(search_query=name)
            if folders and len(folders):
                for folder in folders:
                    if folder.Name == name:
                        folder_id = folder.Id
                        self._set_external_id(folder_id, external_id)
                        return folder_id

            new_folder = self._session_api.addFolder(name)
            if not new_folder:
                raise InvalidParamException('Cannot add folder: %s' % name)

            new_folder_id = new_folder.Id
            self._set_external_id(new_folder_id, external_id)
            return new_folder_id
        except Exception as ex:
            raise InvalidParamException('Cannot add folder: %s' % ex)

    def _set_external_id(self, folder_id, external_id):
        if external_id and len(external_id):
            self._session_api.updateFolderExternalIdWithProvider(
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
        key = course_event_key(session['uwnetid'], session['name'],
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
                    messages.append('Invalid UWNetId %s' % creator)

        for creator in current_creators:
            if creator not in folder_creators:
                try:
                    deleted_creator_ids.append(
                        self._get_panopto_user_id(creator))
                except PanoptoUserException as ex:
                    messages.append('Invalid UWNetId %s' % creator)

        if len(new_creator_ids):
            try:
                self._access_api.grantUsersAccessToFolder(
                    folder_id, new_creator_ids, 'Creator')
            except PanoptoAPIException as ex:
                match = re.match(r'.*Server raised fault: \'(.+)\'$', str(ex))
                messages.append('%s: %s' % (creator, match.group(1) if (
                    match) else str(ex)))

        if len(deleted_creator_ids):
            try:
                self._access_api.revokeUsersAccessFromFolder(
                    folder_id, deleted_creator_ids, 'Creator')
            except PanoptoAPIException as ex:
                match = re.match(r'.*Server raised fault: \'(.+)\'$', str(ex))
                messages.append('%s: %s' % (creator, match.group(1) if (
                    match) else str(ex)))

        return messages

    def _get_panopto_user_id(self, netid):
        key = r'%s\%s' % (getattr(settings, 'PANOPTO_API_APP_ID', ''), netid)
        user = self._user_api.getUserByKey(key)
        if (not user or
                user['UserId'] == '00000000-0000-0000-0000-000000000000'):
            raise PanoptoUserException('Unprovisioned UWNetId: %s' % (netid))

        return user['UserId']


class SessionPublic(RESTDispatch):
    def __init__(self):
        self._audit_log = logging.getLogger('audit')

    def get(self, request, *args, **kwargs):
        self._access_api = AccessManagement()
        session_id = kwargs.get('session_id')
        if session_id:
            raw_access = self._access_api.getSessionAccessDetails(session_id)
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
            self._access_api = AccessManagement()
            self._access_api.updateSessionIsPublic(session_id, is_public)
            self._audit_log.info('%s set %s public access to %s' % (
                request.user, session_id, is_public))

            return self.json_response({
                'recording_id': session_id
            })
        except InvalidParamException as ex:
            return self.error_response(400, "%s" % ex)
        except Exception as ex:
            return self.error_response(500, "Unable to save session: %s" % ex)

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
            self._session_api = SessionManagement()
            raw_session = self._session_api.getSessionsById([session_id])[0][0]
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
            self._session_api = SessionManagement()
            is_broadcast = self._valid_boolean(
                data.get("is_broadcast", False), 'bad broadcast flag')
            self._session_api.updateSessionIsBroadcast(session_id,
                                                       is_broadcast)
            self._audit_log.info('%s set %s broadcast to %s' % (
                request.user, session_id, is_broadcast))

            return self.json_response({
                'recording_id': session_id
            })
        except InvalidParamException as ex:
            return self.error_response(400, "%s" % ex)
        except Exception as ex:
            return self.error_response(500, "Unable to save session: %s" % ex)

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
            self._recorder_api = RemoteRecorderManagement()
            raw_session = self._session_api.getSessionsById([session_id])[0][0]
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
            self._recorder_api = RemoteRecorderManagement()
            session_id = kwargs.get('session_id')
            data = json.loads(request.body)
            start_time = self._valid_time(data.get("start", "").strip())
            end_time = self._valid_time(data.get("end", "").strip())

            self._recorder_api.updateRecordingTime(
                session_id, start_time, end_time)

            self._audit_log.info('%s set %s start/stop to %s and %s' % (
                request.user, session_id, start_time, end_time))

            return self.json_response({
                'recording_id': session_id
            })
        except InvalidParamException as ex:
            return self.error_response(400, "%s" % ex)
        except Exception as ex:
            return self.error_response(500, "Unable to save session: %s" % ex)

    def _valid_time(self, time):
        if time and len(time):
            return time

        raise InvalidParamException('bad time value')
