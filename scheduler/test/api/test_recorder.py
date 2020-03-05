from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse_lazy
from scheduler.views.api.recorder import Recorder
import json
import logging


# silence suds debugging telemetry
logging.getLogger('suds').setLevel(logging.ERROR)


class TestAPIRecorder(TestCase):
    def test_get_recorders(self):
        recorder = Recorder()
        url = reverse_lazy('api_recorder')
        request = RequestFactory().get(url)

        response = recorder.get(request)
        recorders = json.loads(response.content)
        self.assertEqual(len(recorders), 1)
        self.assertEqual(recorders[0]['external_id'], '4991')

    def test_get_recorder(self):
        recorder = Recorder()
        request = RequestFactory().get(
            "/api/v1/recorder/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        response = recorder.get(request)
        recorders = json.loads(response.content)
        self.assertEqual(recorders[0]['external_id'], '4991')
