from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse_lazy
from scheduler.test import get_user
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

        sessions['uwnetid'] = 'jfaculty'
        sessions['end_time'] = sessions['start_time']
        sessions['recorder_id'] = '22e12346-1234-1234-4321-12347f1234c5'
        sessions['folder_external_id'] = '2015-autumn-PSYCH-101-A'
        sessions['key'] = '9AC7325FB31465FF946FFFC5514E35CEB3F42C38'
        request = RequestFactory().post(
            url, sessions, content_type="application/json")
        request.user = get_user('jfaculty')
        response = session.post(request)
        self.assertEqual(response.status_code, 200)
