# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse_lazy
from scheduler.test import get_user
from scheduler.views.api.session import (
    Session, SessionPublic, SessionBroadcast, SessionRecordingTime)
import json
import logging


# silence suds debugging telemetry
logging.getLogger('suds').setLevel(logging.ERROR)

course_test_override = override_settings(
    USER_MODULE='scheduler.org.uw.user',
    COURSES_MODULE='scheduler.org.uw.course',
    RESERVATIONS_MODULE='scheduler.org.uw.reservations'
)


@course_test_override
class TestAPISession(TestCase):
    def test_api_session(self):
        session = Session()
        url = reverse_lazy('api_session')
        session_id = "673fcde2-4d70-4610-89b3-3638684cf90c"
        request = RequestFactory().get("{}{}".format(url, session_id))
        response = session.get(request, session_id=session_id)
        sessions = json.loads(response.content)
        self.assertEqual(sessions['state'], 'Scheduled')
        self.assertEqual(sessions['is_public'], False)

        sessions['loginid'] = 'jfaculty'
        sessions['end_time'] = sessions['start_time']
        sessions['recorder_id'] = '22e12346-1234-1234-4321-12347f1234c5'
        sessions['folder_id'] = 'c9123444-0000-0000-0000-ab71234c452d'
        sessions['key'] = '25978DBA8C508FA66BCC29507DA6094446DACC55'

        request = RequestFactory().post(
            url, sessions, content_type="application/json")
        request.user = get_user('jfaculty')
        response = session.post(request)
        self.assertEqual(response.status_code, 200)

        response = session.put(request)
        self.assertEqual(response.status_code, 200)

        response = session.post(request)
        self.assertEqual(response.status_code, 200)

        request = RequestFactory().delete(
            "{}?{}".format(
                url,
                '&'.join(['loginid=jfaculty',
                          'eid=2015-autumn-PSYCH-101-A',
                          'rid=22e12346-1234-1234-4321-12347f1234c5',
                          'rstart={}'.format(sessions['start_time']),
                          'rend={}'.format(sessions['end_time']),
                          'key=73D5C615E672D76777698EC8180EE4CD58A55C15'])))
        request.user = get_user('jfaculty')
        response = session.delete(request, session_id=session_id)
        self.assertEqual(response.status_code, 200)
        sessions = json.loads(response.content)
        self.assertEqual(sessions["deleted_recording_id"], session_id)

    def test_api_session_public(self):
        session = SessionPublic()
        session_id = "61234de2-1234-1234-89b3-3638684cf90c"
        url = reverse_lazy('api_session_public',
                           kwargs={'session_id': session_id})
        request = RequestFactory().get("{}".format(url))
        request.user = get_user('jfaculty')
        response = session.get(request, session_id=session_id)
        self.assertEqual(response.status_code, 200)

        sessions = json.loads(response.content)
        self.assertEqual(sessions['is_public'], True)

        request = RequestFactory().put("{}".format(url),
                                       data=json.dumps(sessions),
                                       content_type='application/json')
        request.user = get_user('jfaculty')

        response = session.put(request, session_id=session_id)
        self.assertEqual(response.status_code, 200)

        sessions = json.loads(response.content)
        self.assertEqual(sessions['recording_id'], session_id)

    def test_api_session_broadcast(self):
        session = SessionBroadcast()
        session_id = "61234de2-1234-1234-89b3-3638684cf90c"
        url = reverse_lazy('api_session_broadcast',
                           kwargs={'session_id': session_id})
        request = RequestFactory().get("{}".format(url))
        request.user = get_user('jfaculty')
        response = session.get(request, session_id=session_id)
        self.assertEqual(response.status_code, 200)

        sessions = json.loads(response.content)
        self.assertEqual(sessions['is_broadcast'], True)

        request = RequestFactory().put("{}".format(url),
                                       data=json.dumps(sessions),
                                       content_type='application/json')
        request.user = get_user('jfaculty')

        response = session.put(request, session_id=session_id)
        self.assertEqual(response.status_code, 200)

        sessions = json.loads(response.content)
        self.assertEqual(sessions['recording_id'], session_id)

    def test_api_session_recording_time(self):
        session = SessionRecordingTime()
        session_id = "61234de2-1234-1234-89b3-3638684cf90c"
        url = reverse_lazy('api_session_recording_time',
                           kwargs={'session_id': session_id})
        request = RequestFactory().get("{}".format(url))
        request.user = get_user('jfaculty')
        response = session.get(request, session_id=session_id)
        self.assertEqual(response.status_code, 200)

        sessions = json.loads(response.content)
        self.assertTrue('start' in sessions)
        self.assertTrue('end' in sessions)

        request = RequestFactory().put("{}".format(url),
                                       data=json.dumps(sessions),
                                       content_type='application/json')
        request.user = get_user('jfaculty')
        response = session.put(request, session_id=session_id)
        self.assertEqual(response.status_code, 200)

        sessions = json.loads(response.content)
        self.assertEqual(sessions['recording_id'], session_id)
