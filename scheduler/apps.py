from django.apps import AppConfig
from restclients_core.dao import MockDAO
import os


class SchedulerConfig(AppConfig):
    name = 'scheduler'

    def ready(self):
        mocks = os.path.join(os.path.dirname(__file__), 'resources')
        MockDAO.register_mock_path(mocks)
