from django.test import TestCase
from scheduler.utils import space_events_and_recordings


class TestSpaceEventAndRecordings(TestCase):
    def test_space_events_and_recordings(self):
        events = space_events_and_recordings(
            {
                'space_id': 4991,
                'start_dt': '2015-12-02T08:00:00.000Z'
            })

        self.assertEqual(len(events), 1)
