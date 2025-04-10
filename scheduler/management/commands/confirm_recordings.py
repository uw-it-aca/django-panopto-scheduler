# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from prometheus_client import Gauge
from scheduler.course import Course
from scheduler.reservations import Reservations
from panopto_client.session import SessionManagement
from panopto_client.remote_recorder import RemoteRecorderManagement
from scheduler.utils.monitor import email_addresses_from_group
import logging


# disable chatty libraries
logging.getLogger('suds').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class UnassignedRecorder(Exception):
    pass


class Command(BaseCommand):
    help = "Matchrecording session dates to SWS meeting times"

    _recorders = {}
    _sessions = {}
    _metrics = None
    _name_mismatch = []
    _recorder_missing = []
    _recorder_mismatch = []
    _disconnected = []
    _multiple_recorders = []

    def handle(self, *args, **options):
        session_api = SessionManagement()
        recorder_api = RemoteRecorderManagement()
        self._metrics = Metrics()

        for recorder in recorder_api.listRecorders():
            if recorder.ExternalId:

                self.recorders(recorder.ExternalId, recorder)

                if not recorder.ScheduledRecordings:
                    self.note(
                        ('RECORDER {} "{}" ({}): '
                         'no scheduled recordings').format(
                             recorder.Id, recorder.Name, recorder.ExternalId))
                    continue

                self.note('RECORDER {} "{}" ({}): gathering schedule'.format(
                    recorder.Id, recorder.Name, recorder.ExternalId))

                for session in session_api.getSessionsById(
                        recorder.ScheduledRecordings[0])[0]:
                    if session.ExternalId:
                        try:
                            # 2021-autumn-BIOC-440-A-2021-10-20
                            year, term, cur, course, section, yy, mm, dd = \
                                tuple(session.ExternalId.split('-'))
                        except ValueError:
                            self.note(
                                "Unexpected session ExternalId: {}".format(
                                    session.ExternalId))
                            continue

                        course_id = "{}-{}-{}-{}-{}".format(
                            year, term, cur, course, section)

                        self.sessions(course_id, recorder.Id, session)
            else:
                self.note('RECORDER {} "{}": not in scheduler'.format(
                    recorder.Id, recorder.Name))

        for course_id, recorders in self.sessions().items():
            course = Course(course_id)
            event = Reservations().get_event_by_course(course)

            if event.is_crosslisted:
                course = course.get_crosslisted_course()

            self.note("COURSE {}: validating {} meetings".format(
                course_id, len(event.reservations)))

            for rsv in event.reservations:
                if rsv.space_id and rsv.is_instruction:
                    name, external_id = course.panopto_course_session(
                        rsv.start_datetime)

                    try:
                        course_recorder = self.recorders(rsv.space_id)
                    except UnassignedRecorder:
                        recorder = self.get_recorder(course_id, external_id)
                        if recorder:
                            self._recorder_missing.append({
                                'course_external_id': external_id,
                                'scheduled': recorder,
                                'meeting_space_id': rsv.space_id})
                        self.note("Meeting {} in {} has no recorder{}".format(
                            external_id, rsv.space_id,
                            ' BUT scheduled as {} in {} ({})'.format(
                                recorder['recording_name'],
                                recorder['recorder_name'],
                                recorder['recorder_id']) if recorder else ''))
                        continue

                    try:
                        session = recorders[course_recorder['id']][external_id]
                    except KeyError:
                        # no scheduled recording for meeting
                        continue

                    self.confirm_recorder(
                        external_id, course_recorder, session)

                    self.confirm_recorder_state(course_recorder, session)

                    self.confirm_session_name(course_id, name, session)

        self.notify()

    def confirm_recorder(self, external_id, course_recorder, session):
        if course_recorder['id'] != session['recorder_id']:
            self._metrics.recorder_mismatch()
            message = ('MISMATCH RECORDER {}: '
                       'meeting in {} "{}", '
                       'recording in {} "{}"').format(
                           external_id,
                           course_recorder['id'],
                           course_recorder['name'],
                           session['recorder_id'],
                           self.recorders(recorder_id=session[
                               'recorder_id'])['name'])
            self.note(message)
            self._recorder_mismatch.append({
                "external_id": external_id,
                "course_recorder_id": course_recorder['id'],
                "course_recorder_name": course_recorder['name'],
                "session_recorder_id": session['recorder_id'],
                "session_recorder_name": self.recorders(recorder_id=session[
                    'recorder_id'])['name']})

    def confirm_recorder_state(self, course_recorder, session):
        if course_recorder['state'].lower() == 'disconnected':
            message = 'DISCONNECTED RECORDER for session {}: {} "{}"'.format(
                session['name'], course_recorder['id'],
                course_recorder['name'])
            self.note(message)
            self._disconnected.append({
                'session_name': session['name'],
                'recorder_id': course_recorder['id'],
                'recorder_name': course_recorder['name']})

    def confirm_session_name(self, course_id, name, session):
        if name != session['name']:
            self._metrics.name_mismatch()
            message = ('MISMATCH NAME {}: "{}" does '
                       'not match session name "{}"').format(
                           course_id, name, session['name'])
            self.note(message)
            self._name_mismatch.append({
                'course_id': course_id,
                'given_name': name,
                'session_name': session['name']})

    def sessions(self, course_id=None, recorder_id=None, session=None):
        if course_id and recorder_id:
            if session:
                if course_id not in self._sessions:
                    self._sessions[course_id] = {}

                if recorder_id not in self._sessions[course_id]:
                    self._sessions[course_id][recorder_id] = {}

                self._sessions[course_id][recorder_id][session.ExternalId] = {
                    'recorder_id': recorder_id,
                    'name': session.Name
                }

            return self._sessions[course_id][recorder_id]

        return self._sessions

    def get_recorder(self, course_id, external_id):
        for recorder_id, recordings in self._sessions[course_id].items():
            if external_id in recordings:
                recorder_id = recordings[external_id]['recorder_id']
                for space_id, recorder in self._recorders.items():
                    if recorder_id == recorder['id']:
                        return {
                            'recorder_id': recorder_id,
                            'recorder_name': recorder['name'],
                            'recording_name': recordings[external_id]['name']
                        }

        return None

    def recorders(self, space_id=None, recorder=None, recorder_id=None):
        if space_id:
            if recorder:
                if space_id in self._recorders:
                    current_recorder = self._recorders[space_id]
                    current_disconnected = (
                        current_recorder['state'].lower() == 'disconnected')
                    disconnected = (recorder.State.lower() == 'disconnected')
                    message = (
                        'MULTIPLE RECORDERS in space id {}: '
                        '{} "{}"{} and {} "{}"{}').format(
                            recorder.ExternalId,
                            current_recorder['id'], current_recorder['name'],
                            " (DISCONNECTED)" if current_disconnected else "",
                            recorder.Id, recorder.Name,
                            " (DISCONNECTED)" if disconnected else "")

                    self._multiple_recorders.append(message)
                    self.note(message)
                    if not current_disconnected or disconnected:
                        return None

                # authoritative space_id/recorder_id binding
                self._recorders[space_id] = {
                    'id': recorder.Id,
                    'name': recorder.Name,
                    'state': recorder.State
                }

            try:
                return self._recorders[space_id]
            except KeyError:
                raise UnassignedRecorder()

        if recorder_id:
            for s, r in self._recorders.items():
                if r['id'] == recorder_id:
                    return r

            raise UnassignedRecorder()

        return self._recorders

    def note(self, message):
        logger.info("{}".format(message))

    def notify(self):
        self._metrics.publish()

        monitor_group = getattr(settings, 'PANOPTO_MONITOR_GROUP')
        if (monitor_group and (len(self._recorder_mismatch)
                               or len(self._recorder_missing)
                               or len(self._name_mismatch)
                               or len(self._disconnected))):
            recipients = email_addresses_from_group(monitor_group)
            sender = getattr(settings, "EMAIL_REPLY_ADDRESS",
                             "scheduler-noreply@uw.edu")
            subject = "{} Panopto Scheduler Recorder Mismatches".format(
                "URGENT:" if len(self._recorder_mismatch) else "")
            body = "Panopto scheduler found the following:\n\n"

            if len(self._recorder_mismatch):
                body += ("\n\nEach recording session below is "
                         "associated with a recorder that\n"
                         "is not in the assigned class meeting room.\n\n"
                         "Session ID                            "
                         "Session Recorder                                  "
                         "Meeting Location\n")

                for mismatch in self._recorder_mismatch:
                    body += "{:<38}{:<50}{} ({})\n".format(
                        mismatch["external_id"],
                        "{} ({})".format(mismatch["session_recorder_name"],
                                         mismatch["session_recorder_id"]),
                        mismatch["course_recorder_name"],
                        mismatch["course_recorder_id"])

            if len(self._recorder_missing):
                body += ("\n\nRecording sessions below are "
                         "associated with a course meeting in a location\n"
                         "that has no recorder.  The meeting has a recording"
                         "scheduled in a\nprevious location.\n\n"
                         "Course Meeting ID                     "
                         "Recording Name         "
                         "Recorder Name   "
                         "Recorder ID\n")

                for missing in self._recorder_missing:
                    body += "{:<38}{:<24}{:<16} ({})\n".format(
                        missing["course_external_id"],
                        missing["scheduled"]["recording_name"],
                        missing["scheduled"]["recorder_name"],
                        missing["scheduled"]["recorder_id"])

            if len(self._disconnected):
                body += ("\n\nBelow are recording sessions that are "
                         "associated with a disconnected camera.\n"
                         "Not necessarily a problem, but if the date "
                         "implied by the session id is\n"
                         "soon, further inspection may be useful.\n\n")

                disc_rec = {}
                for disconnected in self._disconnected:
                    if disconnected['recorder_id'] not in disc_rec:
                        disc_rec[disconnected['recorder_id']] = {
                            'name': disconnected['recorder_name'],
                            'recordings': []}

                        disc_rec[disconnected['recorder_id']][
                            'recordings'].append(disconnected['session_name'])

                        for k, v in disc_rec.items():
                            body += ("Disconnected recorder: {} ()\n"
                                     "Session Names:").format(
                                         v['recorder_name'] if (
                                             'recorder_name' in v) else (
                                                 "UNNAMED RECORDER"),
                                         k)
                            for r in v['recordings']:
                                body += "       {}\n".format(r)

            if len(self._name_mismatch):
                body += ("\n\nBelow are sessions found with names "
                         "that do not match the name\n"
                         "the scheduler assigned.  Generally can be "
                         "IGNORED, but if the name\n"
                         "indicates an entirely different course, "
                         "then investigation may be\n"
                         "helpful\n\n"
                         "Recording ID                    "
                         "Assigned Name                 Changed Name\n")

                for mismatch in self._name_mismatch:
                    body += "{:<32}{:<30}{}\n".format(
                        mismatch['course_id'],
                        mismatch['given_name'],
                        mismatch['session_name'])

            if len(self._multiple_recorders):
                body += ("\n\nBelow are spaces that have been found to "
                         "contain multiple recorders.\nThe scheduler can "
                         "only schedule recordings in spaces that have a "
                         "single\nrecorder.  As long as only one recorder "
                         "is enabled, it should be fine.\n\n")

                for multi in self._multiple_recorders:
                    body += "{}\n".format(multi)

            message = EmailMessage(subject, body, sender, recipients)
            message.send()


class Metrics:
    def __init__(self):
        self._mismatched_recorders_count = 0
        self._mismatched_names_count = 0
        self._mismatched_recorders = Gauge(
            'mismatched_recorder',
            ('Number of recorder ids in meeting space '
             'does not match session recorder id'),
            ['job'])
        self._mismatched_names = Gauge(
            'mismatched_name',
            'Number of assigned meeting names that do not match session name',
            ['job'])

    def recorder_mismatch(self):
        self._mismatched_recorders_count += 1

    def name_mismatch(self):
        self._mismatched_names_count += 1

    def publish(self):
        self._mismatched_recorders.labels(
            'confirm_recordings').set(self._mismatched_recorders_count)
        self._mismatched_names.labels(
            'confirm_recordings').set(self._mismatched_names_count)
