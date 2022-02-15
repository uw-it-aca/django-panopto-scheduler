# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse_lazy
from scheduler.views.api.space import Space
import json
import logging


# silence suds debugging telemetry
logging.getLogger('suds').setLevel(logging.ERROR)


class TestAPISpace(TestCase):
    def test_get_spaces(self):
        space = Space()
        url = reverse_lazy('api_space')
        request = RequestFactory().get(url)

        response = space.get(request)
        self.assertEqual(response.status_code, 200)

        spaces = json.loads(response.content)
        self.assertEqual(len(spaces), 3)

    def test_get_space(self):
        space = Space()
        url = reverse_lazy('api_space')
        space_id = "4991"
        request = RequestFactory().get("{}{}".format(url, space_id))

        response = space.get(request, space_id=space_id)
        self.assertEqual(response.status_code, 200)

        spaces = json.loads(response.content)
        self.assertEqual(spaces['space_id'], '4991')
