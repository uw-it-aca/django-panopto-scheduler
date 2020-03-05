from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse_lazy
from scheduler.views.api.session import Session
import json
import logging


# silence suds debugging telemetry
logging.getLogger('suds').setLevel(logging.ERROR)


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

        sessions['end_time'] = sessions['start_time']
        sessions['recorder_id'] = '22e12346-1234-1234-4321-12347f1234c5'
        sessions['folder_external_id'] = '2015-autumn-PSYCH-101-A'
        request = RequestFactory().post(
            url, sessions, content_type="application/json")
        response = session.post(request)
