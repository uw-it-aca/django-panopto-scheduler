# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.management.base import BaseCommand
from prometheus_client import CollectorRegistry, Counter, push_to_gateway
from uw_sws.section import get_section_by_url
from panopto_client.session import SessionManagement
from panopto_client.remote_recorder import RemoteRecorderManagement
from uw_r25.events import get_event_by_alien_id
from scheduler.utils import (
    r25_alien_uid, panopto_course_session, get_sws_section, canvas_course_id)
from scheduler.utils.validation import Validation
import os
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

                        self.sessions(course_id, session)
            else:
                self.note('RECORDER {} "{}": not in scheduler'.format(
                    recorder.Id, recorder.Name))

        for course_id, sessions in self.sessions().items():
            validation_api = Validation()
            course = validation_api.course_id(course_id)
            event = get_event_by_alien_id(r25_alien_uid(course))

            # cross listed?
            if len(event.binding_reservations):
                joint = []

                # default to Canvas course that student
                # sections are provisioned
                section = get_sws_section(course)
                if not section.is_withdrawn and len(
                        section.joint_section_urls):
                    joint_course_ids = [canvas_course_id(course)]
                    for url in section.joint_section_urls:
                        try:
                            joint_section = get_section_by_url(url)
                            if not joint_section.is_withdrawn:
                                joint_course_id = \
                                    joint_section.canvas_course_sis_id()
                                joint_course_ids.append(joint_course_id)
                                c = validation_api.course_id(joint_course_id)
                                joint.append("{} {} {}".format(
                                    c.curriculum, c.number, c.section))
                        except Exception:
                            continue
        
                    if len(joint_course_ids):
                        joint_course_ids.sort()
                        course = validation_api.course_id(joint_course_ids[0])

            self.note("COURSE {}: validating {} meetings".format(
                course_id, len(event.reservations)))

            for rsv in event.reservations:
                if rsv.space_reservation:
                    name, external_id = panopto_course_session(
                        course, rsv.start_datetime)

                    try:
                        space_id = rsv.space_reservation.space_id
                        course_recorder = self.recorders(space_id)
                    except UnassignedRecorder:
                        self._note("Meeting {} in {} has no recorder".format(
                            external_id, space_id))
                        continue

                    try:
                        session = sessions[external_id]
                    except KeyError:
                        # no scheduled recording for meeting
                        continue

                    self.confirm_recorder(
                        external_id, course_recorder, session)

                    self.confirm_session_name(course_id, name, session)

        self._metrics.push()

    def confirm_recorder(self, external_id, course_recorder, session):
        if course_recorder['id'] != session['recorder_id']:
            self._metrics.recorder_mismatch()
            self.note(
                ('MISMATCH RECORDER {}: '
                 'meeting in {} "{}", '
                 'recording in {} "{}"').format(
                     external_id,
                     course_recorder['id'],
                     course_recorder['name'],
                     session['recorder_id'],
                     self.recorders(recorder_id=session[
                         'recorder_id'])['name']))

    def confirm_session_name(self, course_id, name, session):
        if name != session['name']:
            self._metrics.name_mismatch()
            self.note(
                ('MISMATCH NAME {}: "{}" does '
                 'not match session name "{}"').format(
                     course_id, name, session['name']))

    def sessions(self, course_id=None, session=None):
        if course_id:
            if session:
                if course_id not in self._sessions:
                    self._sessions[course_id] = {}

                self._sessions[course_id][session.ExternalId] = {
                    'recorder_id': session.RemoteRecorderIds[0][0],
                    'name': session.Name
                }

            return self._sessions[course_id]

        return self._sessions

    def recorders(self, space_id=None, recorder=None, recorder_id=None):
        if space_id:
            if recorder:
                if space_id in self._recorders:
                    raise Exception(
                        ('Space ID {} assigned to recorders '
                         '{} "{}" and {} "{}"').format(
                            recorder.ExternalId,
                             self._recorders[space_id]['id'],
                             self._recorders[space_id]['name'],
                            recorder.Name, recorder.Id
                        ))

                # authoritative space_id/recorder_id binding
                self._recorders[space_id] = {
                    'id': recorder.Id,
                    'name': recorder.Name
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
        logger.info("CONFREC: {}".format(message))


class Metrics:
    def __init__(self):
        self._pushgateway = os.getenv('PUSHGATEWAY')
        if self._pushgateway:
            self._registry = CollectorRegistry()
            self._mismatched_recorder_counters = Counter(
                'mismatched_recorder',
                ('Recorder id in meeting space '
                 'does not match session recorder id'),
                registry=self._registry)
            self._mismatched_name_counter = Counter(
                'mismatched_name',
                'Assigned meeting name does not match session name',
                registry=self._registry)

    def recorder_mismatch(self):
        if self._pushgateway:
            self._mismatched_recorder_counter.inc()

    def name_mismatch(self):
        if self._pushgateway:
            self._mismatched_name_counter.inc()

    def push(self):
        if self._pushgateway:
            push_to_gateway('{}:9091'.format(self._pushgateway),
                            job='scheduled_recordings_reconcile',
                            registry=self._registry)


