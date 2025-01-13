# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.apps import AppConfig
from restclients_core.dao import MockDAO
import os


class SchedulerConfig(AppConfig):
    name = 'scheduler'

    def ready(self):
        mocks = os.path.join(os.path.dirname(__file__), 'resources')
        MockDAO.register_mock_path(mocks)
