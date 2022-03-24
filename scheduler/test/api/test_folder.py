# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse_lazy
from scheduler.views.api.folder import Folder
import json
import logging


# silence suds debugging telemetry
logging.getLogger('suds').setLevel(logging.ERROR)


class TestAPIFolder(TestCase):
    def test_get_folders(self):
        folder = Folder()
        url = reverse_lazy('api_folder')
        request = RequestFactory().get("{}{}".format(url, "?search=PSYCH"))

        response = folder.get(request)
        self.assertEqual(response.status_code, 200)

        folders = json.loads(response.content)
        self.assertEqual(len(folders), 1)
        self.assertEqual(
            folders[0]['id'], '30f1234a-1234-1234-1234-60c12345b78e')
