from scheduler.views.rest_dispatch import RESTDispatch
from scheduler.views.api.exceptions import MissingParamException, \
    InvalidParamException
from scheduler.utils import course_event_key
from scheduler.utils.validation import Validation
from panopto_client.session import SessionManagement
from panopto_client.access import AccessManagement
from panopto_client.remote_recorder import RemoteRecorderManagement
from dateutil import parser, tz
import simplejson as json
import logging
import pytz
import re


logger = logging.getLogger(__name__)


class Session(RESTDispatch):
    def __init__(self):
        self._session_api = SessionManagement()
        self._recorder_api = RemoteRecorderManagement()
        self._access_api = AccessManagement()
        self._audit_log = logging.getLogger('audit')

    def GET(self, request, **kwargs):
        session_id = kwargs.get('session_id')
        if session_id:
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

    def POST(self, request, **kwargs):
        try:
            data = json.loads(request.body)
            uwnetid = data.get("uwnetid", "")
            name = self._valid_recording_name(data.get("name", "").strip())
            external_id = self._valid_external_id(
                data.get("external_id", "").strip())
            recorder_id = self._valid_recorder_id(
                data.get("recorder_id", "").strip())
            folder_external_id = data.get("folder_external_id", "").strip()

            # do not permit param tampering
            key = course_event_key(uwnetid, name, external_id,
                                   recorder_id, folder_external_id)
            if key != data.get("key", ''):
                raise InvalidParamException('Invalid Client Key')

            is_broadcast = self._valid_boolean(data.get("is_broadcast", False))
            is_public = self._valid_boolean(data.get("is_public", False))
            start_time = self._valid_time(data.get("start_time", "").strip())
            end_time = self._valid_time(data.get("end_time", "").strip())
            folder_id = self._valid_folder(data.get("folder_name", "").strip(),
                                           folder_external_id)

            session = self._recorder_api.scheduleRecording(name,
                                                           folder_id,
                                                           is_broadcast,
                                                           start_time,
                                                           end_time,
                                                           recorder_id)
            if session.ConflictsExist:
                conflict = session.ConflictingSessions[0][0]
                start_time = conflict.StartTime
                end_time = conflict.EndTime
                content = {
                    'conflict_name': conflict.SessionName,
                    'conflict_start': start_time.isoformat(),
                    'conflict_end': end_time.isoformat()
                }
                return self.error_response(409, "Schedule Conflict Exists",
                                           content=content)

            session_id = session.SessionIDs[0][0]

            self._session_api.updateSessionExternalId(session_id,
                                                      external_id)

            if is_public:
                self._access_api.updateSessionIsPublic(session_id, True)

            self._audit_log.info('%s scheduled %s for %s from %s to %s' % (
                request.user, external_id, uwnetid, start_time, end_time))

            return self.json_response({
                'recording_id': session_id
            })
        except InvalidParamException as ex:
            return self.error_response(400, "%s" % ex)
        except Exception as ex:
            return self.error_response(500, "Unable to save session: %s" % ex)

    def DELETE(self, request, **kwargs):
        try:
            session_id = self._valid_recorder_id(kwargs.get('session_id'))
            # do not permit param tampering
            key = course_event_key(request.GET.get('uwnetid', ''),
                                   request.GET.get('name', ''),
                                   request.GET.get('eid', ''),
                                   request.GET.get('rid', ''),
                                   request.GET.get('feid', ''))

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
            folders = self._session_api.getAllFoldersByExternalId(
                [external_id])
            if folders and len(folders) and len(folders[0]):
                return folders[0][0].Id

            folders = self._session_api.getFoldersList(search_query=name)
            if folders and len(folders):
                folder_id = folders[0].Id
                self._session_api.updateFolderExternalId(
                    folder_id, external_id)
                return folder_id

            new_folder = self._session_api.addFolder(name)
            if not new_folder:
                raise InvalidParamException('Cannot add folder: %s' % name)

            new_folder_id = new_folder.Id
            self._session_api.updateFolderExternalId(new_folder_id,
                                                     external_id)
            return new_folder_id
        except Exception as ex:
            raise InvalidParamException('Cannot add folder: %s' % ex)

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


class SessionPublic(RESTDispatch):
    def __init__(self):
        self._access_api = AccessManagement()
        self._audit_log = logging.getLogger('audit')

    def GET(self, request, **kwargs):
        session_id = kwargs.get('session_id')
        if session_id:
            raw_access = self._access_api.getSessionAccessDetails(session_id)
            access = {
                'is_public': raw_access['IsPublic']
            }
        else:
            access = {}

        return self.json_response(access)

    def PUT(self, request, **kwargs):
        try:
            session_id = kwargs.get('session_id')
            data = json.loads(request.body)
            is_public = self._valid_boolean(data.get("is_public", False),
                                            'bad public flag')
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
        self._session_api = SessionManagement()
        self._audit_log = logging.getLogger('audit')

    def GET(self, request, **kwargs):
        session_id = kwargs.get('session_id')
        if session_id:
            raw_session = self._session_api.getSessionsById([session_id])[0][0]
            broadcast = {
                'is_broadcast': raw_session['IsBroadcast'],
            }
        else:
            broadcast = {}

        return self.json_response(broadcast)

    def PUT(self, request, **kwargs):
        try:
            session_id = kwargs.get('session_id')
            data = json.loads(request.body)
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
        self._recorder_api = RemoteRecorderManagement()
        self._audit_log = logging.getLogger('audit')

    def GET(self, request, **kwargs):
        session_id = kwargs.get('session_id')
        if session_id:
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

    def PUT(self, request, **kwargs):
        try:
            session_id = kwargs.get('session_id')
            data = json.loads(request.body)
            start_time = self._valid_time(data.get("start", "").strip())
            end_time = self._valid_time(data.get("end", "").strip())
            self._recorder_api.updateRecordingTime(session_id,
                                                   start_time, end_time)
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
