from django.test import TestCase
from scheduler.utils import space_events_and_recordings
import logging


# silence suds debugging telemetry
#logging.getLogger('suds').setLevel(logging.ERROR)


class TestSpaceEventAndRecordings(TestCase):
    def test_space_events_and_recordings(self):
        import pdb; pdb.set_trace()
        events = space_events_and_recordings(
            {
                'space_id': 4991,
                'start_dt': '2015-12-02T08:00:00.000Z'
            })

        self.assertEqual(len(events), 1)
